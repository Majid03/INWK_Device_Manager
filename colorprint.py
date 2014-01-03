#!/usr/bin/python

from termcolor import colored,cprint
from math import floor,ceil
import string

PRINT_LENGTH = 60.0

def start_print(s):
    total_num_star  = PRINT_LENGTH - len(s)
    before_num_star = floor(total_num_star/2)
    after_num_star  = ceil(total_num_star/2)
    s = int(before_num_star) * "*" + s + int(after_num_star) * "*"
    cprint(s,"red","on_yellow")

def end_print(s):
    total_num_star  = PRINT_LENGTH - len(s)
    before_num_star = floor(total_num_star/2)
    after_num_star  = ceil(total_num_star/2)
    s = int(before_num_star) * "*" + s + int(after_num_star) * "*"
    print("\n")
    cprint(s,"red","on_cyan")

def error_print(s="error is found below"):
    total_num_arrow  = PRINT_LENGTH - len(s)
    before_num_arrow = floor(total_num_arrow/2)
    after_num_arrow  = ceil(total_num_arrow/2)
    s = int(before_num_arrow) * ">" + s.upper() + int(after_num_arrow) * ">"
    cprint(s,"red","on_blue")

