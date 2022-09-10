from __future__ import annotations
import argparse
import shlex
import starstar.argparse as ssargparse
import pytest



def myfunction(aaa, bbb: int=5, *a, wow: int|list, quoi='aaa', **kw):
        '''Look at my function

        I love it so much

        Arguments:
            aaa: first
            bbbb: second thing
            wow (int): ok cool
            quoi (str): wow alright
        '''
        print(aaa,  bbb, a, wow, quoi, kw)

@pytest.fixture
def parser():
    parent = argparse.ArgumentParser()
    parent.add_argument('--extra',  default=5)
    parser = ssargparse.from_func(myfunction, parents=[parent], docstyle='google')
    return parser

def test_underspecified(parser):
    with pytest.raises(SystemExit):
        args = parser.parse_args(shlex.split(""))
        assert vars(args) == dict()

def test_just_enough(parser):
    args = parser.parse_args(shlex.split("1 --wow 3"))
    assert vars(args) == dict(extra=5, aaa=1, bbb=5, a=[], wow=3, quoi='aaa')

def test_extra_args(parser):
    args = parser.parse_args(shlex.split("1 2 3 4 -w 3 --xxx  6 --extra  12 --asdfasdfsadf '[1,2,3]'"))
    assert vars(args) == dict(extra='12', aaa=1, bbb=2, a=[3, 4], wow=3, quoi='aaa', xxx=6, asdfasdfsadf=[1, 2, 3])