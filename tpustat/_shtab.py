from __future__ import annotations

import argparse


def _all_option_strings(parser: argparse.ArgumentParser) -> list[str]:
    options: list[str] = []
    for action in parser._actions:
        for option in action.option_strings:
            options.append(option)
    return sorted(set(options))


def _bash_script(parser: argparse.ArgumentParser) -> str:
    options = " ".join(_all_option_strings(parser))
    prog = parser.prog
    return f"""_{prog}_completion() {{
  local cur
  cur="${{COMP_WORDS[COMP_CWORD]}}"
  COMPREPLY=($(compgen -W "{options}" -- "$cur"))
}}
complete -F _{prog}_completion {prog}
"""


def _zsh_script(parser: argparse.ArgumentParser) -> str:
    options = " ".join(_all_option_strings(parser))
    prog = parser.prog
    return f"""#compdef {prog}
local -a opts
opts=({options})
_describe 'option' opts
"""


def _tcsh_script(parser: argparse.ArgumentParser) -> str:
    options = " ".join(_all_option_strings(parser))
    prog = parser.prog
    return f"complete {prog} 'p/*/({options})/'\n"


class _PrintCompletion(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        generators = {
            "bash": _bash_script,
            "zsh": _zsh_script,
            "tcsh": _tcsh_script,
        }
        print(generators[values](parser), end="")
        parser.exit()


def add_argument_to(parser: argparse.ArgumentParser, **_: object) -> None:
    parser.add_argument(
        "--print-completion",
        choices=("bash", "zsh", "tcsh"),
        action=_PrintCompletion,
        help="Print a shell completion script",
    )
