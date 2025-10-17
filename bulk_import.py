#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from datetime import datetime
from datetime import timezone


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=365)
    parser.add_argument('--per-day', type=int, default=687)
    parser.add_argument('--target', required=True)
    parser.add_argument('--remote', default=None)
    parser.add_argument('--user-name', default='aethelreborn')
    parser.add_argument('--user-email',
                        default='aethelreborn@users.noreply.github.com')
    args = parser.parse_args()

    source = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(args.target):
        sys.exit('target already exists: ' + args.target)
    os.makedirs(args.target)

    run(['git', 'init', '-q', '-b', 'main'], args.target)
    run(['git', 'config', 'user.name', args.user_name], args.target)
    run(['git', 'config', 'user.email', args.user_email], args.target)
    if args.remote:
        run(['git', 'remote', 'add', 'origin', args.remote], args.target)

    files = []
    for root, dirs, names in os.walk(source):
        dirs[:] = [d for d in dirs if d != '.git']
        for name in names:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, source).replace(os.sep, '/')
            with open(path, 'rb') as handle:
                content = handle.read()
            files.append((rel, content, os.stat(path).st_mode))
    files.sort(key=lambda item: item[0])

    now = datetime.now(timezone.utc).replace(hour=20, minute=0,
                                             second=0, microsecond=0)
    start = int(now.timestamp()) - args.days * 86400

    proc = subprocess.Popen(['git', 'fast-import'], cwd=args.target,
                            stdin=subprocess.PIPE)
    stream = proc.stdin
    ident = (args.user_name + ' <' + args.user_email + '>').encode()

    def line(data):
        stream.write(data + b'\n')

    def data_block(content):
        line(b'data %d' % len(content))
        stream.write(content)
        stream.write(b'\n')

    mark = 0
    for day in range(args.days):
        for minute in range(args.per_day):
            mark += 1
            stamp = start + day * 86400 + minute * 60
            message = datetime.fromtimestamp(
                stamp, timezone.utc).strftime('Contribution: %Y-%m-%d %H:%M')
            line(b'commit refs/heads/main')
            line(b'mark :%d' % mark)
            author = ident + b' ' + str(stamp).encode() + b' +0000'
            line(b'author ' + author)
            line(b'committer ' + author)
            data_block(message.encode())
            if mark > 1:
                line(b'from :%d' % (mark - 1))
            if mark == 1:
                for rel, content, mode in files:
                    keep = 0o755 if mode & 0o111 else 0o644
                    line(b'M %o inline "%s"' % (keep, rel.encode()))
                    data_block(content)
            else:
                line(b'M 100644 inline "README.md"')
                data_block(message.encode() + b'\n')
            line(b'')

    stream.close()
    if proc.wait() != 0:
        sys.exit('fast-import failed')

    run(['git', 'reset', '--hard', '-q', 'main'], args.target)
    count = subprocess.check_output(
        ['git', 'rev-list', '--count', 'main'],
        cwd=args.target).decode().strip()
    head = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'],
        cwd=args.target).decode().strip()
    print('commits: ' + count)
    print('head: ' + head)


if __name__ == '__main__':
    main()
