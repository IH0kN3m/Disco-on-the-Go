#!/usr/bin/env python3
"""Derive private app icons from the supplied game and configure final iPad branding."""
import argparse
from pathlib import Path
from disco_port.branding import prepare, configure_ipad

ROOT=Path(__file__).resolve().parent.parent
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ipad-project',type=Path)
    args=parser.parse_args()
    output=prepare(ROOT)
    if args.ipad_project:
        project=args.ipad_project.resolve()
        if not project.is_relative_to(ROOT/'artifacts'):parser.error('Generated projects must remain under artifacts/')
        configure_ipad(project,output)
    print('Disco on the Go icons prepared locally; supplied artwork remains excluded from Git.')
