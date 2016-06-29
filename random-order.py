#! /usr/bin/env python
from __future__ import print_function

import sys
import os
import random
import optparse


def gather_tests():
    tests = []
    for root, dirs, files in os.walk('test'):
        local_tests = [os.path.join(root, f) for f in files if os.path.splitext(f)[1] == ".py" and str.startswith(f, 'test_')]
        tests.extend(local_tests)
    return tests


def main(parser):
    (options, args) = parser.parse_args()

    if args:
        if len(args) == 1:
            seed = args[0]
        else:
            parser.error("Only one seed is allowed")
    else:
        seed = random.randrange(1, 5000)

    print("Using seed %s" % seed, file=sys.stderr)
    random.seed(seed)

    tests = gather_tests()

    if options.limit:
        tests = random.sample(tests, options.limit)
    else:
        random.shuffle(tests)

    if options.slice:
        start, _sep, end = options.slice.partition(':')
        if start and end:
            tests = tests[int(start):int(end)]
        elif start:
            tests = tests[int(start):]
        elif end:
            tests = tests[:int(end)]

    print(' '.join(tests))


if __name__ == "__main__":
    usage = "usage: %prog [options] SEED"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-l', '--limit', metavar="LIMIT", type="int",
        help="Select no more than LIMIT items to run")
    parser.add_option('-s', '--slice', metavar="START:END",
        help="Use Python slice syntax to select a subset of tests from the returned results. Begins with zero.")

    main(parser)
