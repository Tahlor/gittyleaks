# change into git python

## Problems: in original, too many ()
## Why can't this find everything that "git grep <regexp> $(git rev-list --all)" can?

import re
from sh import git
from sh import rm
import sh
import os
import argparse

class GittyLeak():

    def __init__(self, kwargs=None):
        self.keywords = ['api', 'key', 'username', 'user', 'uname', 'pw', 'password',
                         'pass', 'email', 'mail', 'credentials', 'credential', 'login',
                         'token', 'secret']
        #self.keywords = ['password']
        self.revision_file_regex = '([a-z0-9]{40}):([^:]+):'
        self.ignore_assignment = False
        self.include_binary = False

        assignment = "(\\b|[ ._-])({})[ '\"]*(=|:)[ '\"]*([^'\" ]+)"
        self.assignment_pattern = assignment.format('|'.join(self.keywords))

        self.excluded_value_chars = [
            '.', '[', 'none', 'true', 'false', 'null',
            'default', 'example', 'username', 'email', 'password'
        ]

        self.min_value_length = 4

        self.excluding = None
        self.revision_list = []
        self.user = None
        self.repo = None
        self.link = None
        self.find_anything = None
        self.case_sensitive = False
        self.show_revision_names = False
        self.no_banner = False
        self.delete = None
        self.matched_items = []
        self.verbose = None
        self.no_fancy_color = None
        self.BANNER_WIDTH = 80

        if kwargs is not None:
            self.apply_init_args(kwargs)
        
        if not self.keywords:
            raise Exception("Must have at least 1 keyword")
        print("Searching for {}".format(self.keywords))

    def apply_init_args(self, kwargs):
        for k, v in kwargs.items():
            if not v is None:
                setattr(self, k, v)
                print(k,v)

        if self.find_anything:
            self.excluded_value_chars = []

        if self.excluding is not None:
            self.excluded_value_chars.extend(self.excluding)

        if not self.case_sensitive:
            self.excluded_value_chars = [x.lower() for x in self.excluded_value_chars]

    def clone(self):
        if self.link is not None:
            try:
                pre = get_immediate_subdirectories()
                git('clone', self.link)
                post = get_immediate_subdirectories()
                self.repo = (post - pre).pop()
            except sh.ErrorReturnCode_128:
                pass

        elif self.user is not None:
            try:
                git('clone', 'https://github.com/{}/{}.git'.format(self.user, self.repo))

            except sh.ErrorReturnCode_128:
                pass

        os.chdir(self.repo)

    def get_revision_list(self):
        self.revision_list = git('rev-list', '--all').strip().split('\n')

    def get_git_matches(self, revision):
        try:
            args = ['grep', '-i', '-e', '{}'.format(r'\|'.join(self.keywords)), revision]
            if not self.include_binary:
                args.insert(1,"-I")
            results = str(git(*args, _tty_out=False))
            return results
        # return subprocess.check_output('git grep -i -e
        # "(api\\|key\\|username\\|user\\|pw\\|password\\|pass\\|email\\|mail)" --
        # `git ls-files | grep -v .html` | cat', shell=True).decode('utf8')
        except sh.ErrorReturnCode_1:
            # import traceback
            # traceback.print_exc()
            # # print("ERR")
            return ''
        except:
            print('encoding error at revision: ', revision)
            return ''

    def get_word_matches(self):
        # git grep simple word matches (python processing follows)
        word_matches = set()
        for revision in self.revision_list:
            for m in self.get_git_matches(revision).split('\n'):
                word_matches.add(m)
                #print(m, word_matches)
        return word_matches

    def validated_value(self, v):
        if v.strip():
            if len(v) < self.min_value_length:
                return False
            if self.excluded_value_chars:
                if not self.case_sensitive:
                    v = v.lower()
                if not any([x in v for x in self.excluded_value_chars]):
                    return True
            else:
                return True
        return False

    def get_matches_dict(self):
        matches = {}
        for match in self.get_word_matches():
            if self.case_sensitive:
                m = re.search(self.assignment_pattern, match)
            else:
                m = re.search(self.assignment_pattern, match, re.IGNORECASE)

            if m:
                rev, fname = (re.search(self.revision_file_regex, match).groups())
                key, _, value = m.groups()[1:]
                if self.validated_value(value):
                    appearance = ':'.join(match.split(':')[2:]).strip()
                    identifier = (fname, key, value)
                    if identifier not in matches:
                        matches[identifier] = []
                    matches[identifier].append((appearance, rev))

        return matches

    def get_matches_dict_simple(self):
        matches = {}
        for match in self.get_word_matches():
            rev, fname = (re.search(self.revision_file_regex, match).groups())
            key, _, value = "", match, ""
            appearance = ':'.join(match.split(':')[2:]).strip()
            identifier = (fname, key, value)
            if identifier not in matches:
                matches[identifier] = []
            matches[identifier].append((appearance, rev))

    def printer(self):
        if not self.no_banner:
            print("{}\n{}\n{}".format("-" * self.BANNER_WIDTH,
                "gittyleaks' Bot Detective at work ...".center(self.BANNER_WIDTH),
                "-" * self.BANNER_WIDTH))
        if not self.matched_items:
            print('No matches.')
        if self.verbose:
            self.print_verbose_matches()
        else:
            self.print_matches()

    def print_matches(self):
        if self.matched_items:
            print('----------------------------------------')

        for k, v in self.matched_items.items():
            for appear in set([x[0] for x in v]):
                # 32 is green, 31 is red
                if not self.no_fancy_color:
                    fname = colorize(k[0], '36')
                    appear = appear.replace(k[1], colorize(k[1], '33'))
                    appear = appear.replace(k[2], colorize(k[2], '31'))
                else:
                    fname = k[0]

                print('{}: {}'.format(fname, appear))

    def print_verbose_matches(self):
        for k, v in self.matched_items.items():
            print('file: {}\nwhat: {}\nvalue: {}\nmatch:'.format(*k))
            for appear in set([x[0] for x in v]):
                print('    {}'.format(appear))
            if self.show_revision_names:
                print('-----Revisions--------------------------')
                for x in v:
                    print(x[1])
            else:
                print('num_of_revisions: {}'.format(len(set([x[1] for x in v]))))
            print('----------------------------------------')

    def run(self):
        if (self.user and self.repo) or self.link:
            self.clone()

        self.get_revision_list()

        if self.ignore_assignment:
            self.matched_items = self.get_matches_dict_simple()
            print(self.matched_items)
        else:
            self.matched_items = self.get_matches_dict()

        if self.delete and (self.user and self.repo) or self.link:
            rm('-rf', '../' + self.repo)


def get_immediate_subdirectories():
    return set([fname for fname in os.listdir('.') if os.path.isdir(fname)])


def colorize(val, code):
    return '\x1b[{}m{}\x1b[0m'.format(code, val)


def get_args_parser():
    p = argparse.ArgumentParser(
        description='Discover where your sensitive data has been leaked.')
    p.add_argument('-user', '-u',
                   help='Provide a github username, only if also -repo')
    p.add_argument('-repo', '-r',
                   help='Provide a github repo, only if also -user')
    p.add_argument('-link', '-l',
                   help='Provide a link to clone')
    p.add_argument('-delete', '-d', action='store_true',
                   help='If cloned, remove the repo afterwards.')
    p.add_argument('--find-anything', '-a', action='store_true',
                   help='flag: If you want to find anything remotely suspicious.')
    p.add_argument('--case-sensitive', '-c', action='store_true',
                   help='flag: If you want to be specific about case matching.')
    p.add_argument('--excluding', '-e', nargs='+',
                   help='List of words that are ignored occurring as value.')
    p.add_argument('--verbose', '-v', action='store_true',
                   help='If flag given, print verbose matches.')
    p.add_argument('--no-banner', '-b', action='store_true',
                   help='Omit the banner at the start of a print statement')
    p.add_argument('--no-fancy-color', '-f', action='store_true',
                   help='Do not colorize output')
    p.add_argument('--keywords', '-k', nargs='+',
                   help='Override default keywords')
    p.add_argument('--ignore_assigment', '-i', action='store_true',
                   help='Just look for keywords, don\'t require =: etc.')
    p.add_argument('--include_binary', action='store_true',
                   help='Look in binary flags')

    return p


def main():
    """ This is the function that is run from commandline with `gittyleaks` """
    args = get_args_parser().parse_args()
    gl = GittyLeak(args.__dict__)
    try:
        gl.run()
    except KeyboardInterrupt:
        print('gittyleaks user interupted')
    gl.printer()
