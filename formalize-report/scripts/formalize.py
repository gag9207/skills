#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""보고서 문어체 정규화 도구.

references/rules.tsv 의 규칙을 순서대로 적용한다.
인용문·코드·서식 원문은 마스킹하여 치환에서 제외한다.

    --scan    구어체 후보를 찾아 문맥과 함께 출력한다 (파일 변경 없음)
    --dry     치환 목록만 출력한다 (파일 변경 없음)
    --apply   실제로 치환한다
    --verify  잔여 구어체·태그 정합·보호 구간 보존을 점검한다

    --backup <디렉토리>   --apply 전에 원본을 복사한다
    --baseline <디렉토리> --verify 시 대조할 원본 디렉토리
    --rules <경로>        규칙표 경로 (기본: 스킬의 references/rules.tsv)

사용 예:
    python3 formalize.py --scan  "Project Management/*.html"
    python3 formalize.py --dry   "Project Management/*.html"
    python3 formalize.py --apply "Project Management/*.html" --backup /tmp/before
    python3 formalize.py --verify "Project Management/*.html" --baseline /tmp/before
"""
import argparse
import glob as globmod
import html as htmlmod
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RULES = os.path.join(HERE, '..', 'references', 'rules.tsv')

# ── 치환에서 제외할 보호 구간 ────────────────────────────────────────
# 새 유형의 인용 구간이 나오면 여기에 추가한다.
PROTECT_HTML = [
    (re.compile(r'<style.*?</style>', re.S), 'STYLE'),
    (re.compile(r'<script.*?</script>', re.S), 'SCRIPT'),
    (re.compile(r'<div class="guide">.*?</div>', re.S), 'GUIDE'),   # 서식이 정한 작성 요령
    (re.compile(r'<blockquote.*?</blockquote>', re.S), 'QUOTE'),
    (re.compile(r'<pre.*?</pre>', re.S), 'PRE'),
    (re.compile(r'<code>.*?</code>', re.S), 'CODE'),
]
PROTECT_MD = [
    (re.compile(r'^```.*?^```', re.S | re.M), 'FENCE'),
    (re.compile(r'`[^`\n]+`'), 'INLINE'),
    (re.compile(r'^>.*$', re.M), 'QUOTE'),
]

# ── 스캔이 찾아 낼 구어체 후보 ──────────────────────────────────────
# 오탐이 섞이므로 반드시 문맥을 읽고 판정한다. (예: "참여기관"에 "여기"가 포함됨)
SCAN = {
    'R1 접속어': ['그런데', '그래서 ', '하지만', '다시 말해', '그러니까'],
    'R2 고유어술어': ['넘어선', '넘긴', '만들', '올랐', '올라갔', '떨어진', '늘어', '줄었',
                  '잃는', '잃었', '훑', '깨워', '쪼개', '잘라', '밀어내', '견디', '죽지'],
    'R3 의존명사': ['가운데'],
    'R4 연결어미': ['하더라도', '이라도 '],
    'R5 지시어': ['그것', '이것', '여기에', '이 한 권', '이 값', '이 수치'],
    'R6 구어부사': ['아예', '애초에', '그냥', '사실상', '제각각', '통째로', '마땅치', '몰아넣'],
    # R7 은 '않다' 계열로 통일한다. 따라서 잔재인 '아니하-' 계열을 후보로 잡는다.
    # 형용사 '아니다'(아니라·아니면·아니 된다)는 대상이 아니므로 '아니하'로만 탐지한다.
    'R7 부정표현': ['아니하', '아니한', '아니할', '아니함'],
    'R8 의문형제목': ['하는가</h', '있는가</h', '쓰이는가</h', '부족한가</h'],
}


def load_rules(path):
    rules = []
    with open(path, encoding='utf-8') as fp:
        for lineno, raw in enumerate(fp, 1):
            line = raw.rstrip('\n')
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                print(f'규칙표 {lineno}행 형식 오류(탭 구분 3개 이상 필요): {line}', file=sys.stderr)
                continue
            rid, old, new = parts[0], parts[1], parts[2]
            scope = parts[3] if len(parts) > 3 else 'common'
            if scope == 'common' and len(old.strip()) < 2:
                print(f'규칙표 {lineno}행 경고: 한 글자를 common 으로 등록하면 '
                      f'다른 낱말을 깨뜨린다 — {old!r}', file=sys.stderr)
            rules.append((rid, old, new, scope))
    return rules


def mask(text, path):
    """보호 구간을 자리표시자로 치환하고, 복원용 사전을 함께 돌려준다."""
    patterns = PROTECT_MD if path.lower().endswith(('.md', '.markdown')) else PROTECT_HTML
    store = {}
    for idx, (rx, tag) in enumerate(patterns):
        def repl(m, tag=tag, idx=idx):
            key = f'\x00{tag}{idx}_{len(store)}\x00'
            store[key] = m.group(0)
            return key
        text = rx.sub(repl, text)
    return text, store


def unmask(text, store):
    for key, val in store.items():
        text = text.replace(key, val)
    return text


def plain(text, path):
    """태그를 걷어 낸 본문. 스캔의 문맥 출력에 사용한다."""
    text, _ = mask(text, path)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = htmlmod.unescape(text)
    return text


def cmd_scan(files):
    for path in files:
        src = open(path, encoding='utf-8').read()
        body = plain(src, path)
        found = []
        for group, needles in SCAN.items():
            for needle in needles:
                target = src if needle.endswith('</h') else body
                n = target.count(needle)
                if n:
                    found.append((group, needle, n))
        if not found:
            print(f'== {os.path.basename(path)} — 후보 없음')
            continue
        print(f'== {os.path.basename(path)}')
        for group, needle, n in sorted(found, key=lambda x: -x[2]):
            print(f'   [{group}] {needle!r} x{n}')
            for line in body.split('\n'):
                line = line.strip()
                if needle in line:
                    for m in re.finditer(re.escape(needle), line):
                        s, e = max(0, m.start() - 40), min(len(line), m.end() + 40)
                        print(f'       …{line[s:e]}…')
                    break
        print()
    print('오탐 주의 — 부분 문자열이 다른 낱말에 포함될 수 있다. 문맥을 읽고 판정할 것.')


def apply_rules(path, rules, write):
    src = open(path, encoding='utf-8').read()
    text, store = mask(src, path)
    log = []
    for rid, old, new, _scope in rules:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            log.append((rid, n, old, new))
    text = unmask(text, store)
    if write and log:
        open(path, 'w', encoding='utf-8').write(text)
    return log


def cmd_run(files, rules, write, backup):
    if write and backup:
        os.makedirs(backup, exist_ok=True)
        for path in files:
            shutil.copy2(path, os.path.join(backup, os.path.basename(path)))
        print(f'원본 {len(files)}개를 {backup} 에 백업하였다.\n')
    total = 0
    for path in files:
        log = apply_rules(path, rules, write)
        if not log:
            continue
        print(f'== {os.path.basename(path)}')
        for rid, n, old, new in log:
            total += n
            o = old if len(old) <= 46 else old[:43] + '…'
            w = new if len(new) <= 46 else new[:43] + '…'
            print(f'   [{rid}] x{n}  {o}  ->  {w}')
        print()
    print(f'총 {total}건 ({"적용함" if write else "시험 적용 — 파일은 변경되지 않았다"})')
    if not write:
        print('목록을 한 줄씩 읽어 의미가 어긋나는 항목이 없는지 확인한 뒤 --apply 로 진행할 것.')


def cmd_verify(files, rules, baseline):
    ok = True

    # 합격/불합격을 가르는 기준은 '규칙표에 등록한 원문이 남아 있는가' 하나다.
    # 스캔 후보는 아직 규칙으로 확정하지 않은 것까지 포함하므로 판정에 쓰지 않는다.
    print('=== 미적용 규칙 (판정 기준) ===')
    for path in files:
        text, _ = mask(open(path, encoding='utf-8').read(), path)
        left = [(rid, old) for rid, old, _new, _s in rules if old in text]
        print(f'  {os.path.basename(path)[:34]:34s} → '
              f'{left if left else "없음 — 규칙이 전부 반영되었다"}')
        if left:
            ok = False

    print('\n=== 남은 스캔 후보 (참고, 판정 무관) ===')
    print('  규칙으로 확정하지 않은 표현이다. 교정이 필요하면 규칙표에 추가한다.')
    for path in files:
        body = plain(open(path, encoding='utf-8').read(), path)
        left = []
        for needles in SCAN.values():
            for needle in needles:
                if needle.endswith('</h'):
                    continue
                n = body.count(needle)
                if n:
                    left.append((needle, n))
        print(f'  {os.path.basename(path)[:34]:34s} → {left if left else "없음"}')

    # 본문이 쓰는 class 가 그 문서의 <style> 안에 정의되어 있는지 확인한다.
    # 다른 문서에서 블록을 옮겨 올 때 CSS 를 함께 옮기지 않으면 레이아웃이 통째로 깨진다.
    print('\n=== class 와 CSS 정의의 일치 ===')
    for path in files:
        if path.lower().endswith(('.md', '.markdown')):
            continue
        src = open(path, encoding='utf-8').read()
        style = '\n'.join(re.findall(r'<style.*?</style>', src, re.S))
        used = set()
        for attr in re.findall(r'class="([^"]+)"', src):
            used.update(attr.split())
        missing = sorted(c for c in used if not re.search(r'\.%s\b' % re.escape(c), style))
        print(f'  {os.path.basename(path)[:34]:34s} → '
              f'{"정의 없는 class: " + str(missing) if missing else "없음 — 전부 정의되어 있다"}')
        if missing:
            ok = False

    print('\n=== 태그 정합 ===')
    for path in files:
        if path.lower().endswith(('.md', '.markdown')):
            continue
        src = open(path, encoding='utf-8').read()
        bad = []
        for tag in ['table', 'tr', 'td', 'th', 'div', 'nav', 'main', 'ol', 'ul',
                    'li', 'p', 'span', 'code', 'b', 'h2', 'h3', 'h4']:
            o = len(re.findall(r'<%s[ >]' % tag, src))
            c = len(re.findall(r'</%s>' % tag, src))
            if o != c:
                bad.append((tag, o, c))
        print(f'  {os.path.basename(path)[:34]:34s} → {bad if bad else "OK"}')
        if bad:
            ok = False

    print('\n=== 보호 구간 보존 ===')
    if not baseline:
        print('  --baseline 미지정. 백업본과 대조하지 못하였다.')
        ok = False
    else:
        for path in files:
            base = os.path.join(baseline, os.path.basename(path))
            if not os.path.exists(base):
                print(f'  {os.path.basename(path)[:34]:34s} → 백업본 없음')
                ok = False
                continue
            _, before = mask(open(base, encoding='utf-8').read(), path)
            _, after = mask(open(path, encoding='utf-8').read(), path)
            same = sorted(before.values()) == sorted(after.values())
            print(f'  {os.path.basename(path)[:34]:34s} → '
                  f'보호 구간 {len(after)}개 {"동일(보존됨)" if same else "★변경됨★"}')
            if not same:
                ok = False

    print('\n판정:', '통과' if ok else '실패 — 위 항목을 교정할 것')
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('pattern', help='대상 파일 glob')
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--scan', action='store_true')
    mode.add_argument('--dry', action='store_true')
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--verify', action='store_true')
    ap.add_argument('--rules', default=DEFAULT_RULES)
    ap.add_argument('--backup')
    ap.add_argument('--baseline')
    args = ap.parse_args()

    files = sorted(globmod.glob(args.pattern))
    if not files:
        print(f'대상 파일이 없다: {args.pattern}', file=sys.stderr)
        return 2

    if args.scan:
        cmd_scan(files)
        return 0
    rules = load_rules(args.rules)
    if not rules:
        print('규칙표가 비어 있다.', file=sys.stderr)
        return 2
    if args.verify:
        return cmd_verify(files, rules, args.baseline)
    cmd_run(files, rules, write=args.apply, backup=args.backup)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except BrokenPipeError:
        # 출력을 head 등으로 자르면 발생한다. 파일 변경은 이미 끝난 뒤이므로 정상 종료한다.
        os._exit(0)
