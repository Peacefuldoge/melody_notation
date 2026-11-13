"""CLI for users and for Codex when MCP is unavailable."""
import argparse
from pathlib import Path
from .core import parse_text, text_from_score
from .midi import export_midi, INSTRUMENTS
from .audio import export_audio
from .png import export_png


def main():
    p = argparse.ArgumentParser(description='Melody Notation numbered-score toolkit')
    commands = p.add_subparsers(dest='command',required=True)
    validate = commands.add_parser('validate',help='validate all measures')
    validate.add_argument('score')
    rend = commands.add_parser('export',help='generate MIDI, audio, or PNG from score')
    rend.add_argument('score'); rend.add_argument('-o','--output',required=True)
    rend.add_argument('-i','--instrument',choices=list(INSTRUMENTS),default='piano')
    rend.add_argument('--sf2',help='SoundFont file (optional; requires fluidsynth executable)')
    rend.add_argument('--bars-per-row',type=int,default=4)
    ocr = commands.add_parser('ocr',help='vision OMR image to editable text (requires API)')
    ocr.add_argument('image'); ocr.add_argument('-o','--output',required=True)
    ocr.add_argument('--model')
    gui = commands.add_parser('gui', help='open PySide6 project workspace')
    gui.add_argument('project', nargs='?', help='optional project folder')
    commands.add_parser('tk-gui', help='open previous Tkinter workspace (legacy)')
    args=p.parse_args()
    if args.command=='gui':
        from .diagnostics import enable_gui_crash_log
        enable_gui_crash_log()
        try:
            from .qt_gui import main as open_gui
        except ImportError as exc:
            if 'PySide6' in str(exc):
                p.error('GUI 需要 PySide6。先运行：python -m pip install -e ".[gui]"')
            raise
        import sys
        return open_gui([sys.argv[0]] + ([args.project] if args.project else []))
    if args.command=='tk-gui':
        from .gui import main as legacy_gui
        return legacy_gui()
    if args.command=='ocr':
        from .vision import transcribe_image
        s, uncertainty=transcribe_image(args.image,model=args.model)
        Path(args.output).write_text(text_from_score(s),encoding='utf-8')
        print('Created draft',args.output,'\nHuman review required:',uncertainty)
        return
    suffix_in=Path(args.score).suffix.lower()
    if suffix_in in ('.mtrack','.drum'):
        from .arrangement import (Arrangement,rendered_events,export_arrangement_midi,export_arrangement_audio)
        from .drums import DrumPattern,export_drum_midi,export_drum_audio
        if suffix_in=='.mtrack':
            source=Arrangement.load(args.score)
            if args.command=='validate':
                count=len(rendered_events(source,args.score))
                print(f'OK: {len(source.tracks)} tracks, {count} audible events');return
            if Path(args.output).suffix.lower()=='.mid':target=export_arrangement_midi(source,args.score,args.output)
            else:target=export_arrangement_audio(source,args.score,args.output)
        else:
            source=DrumPattern.load(args.score)
            if args.command=='validate':
                print(f'OK: {source.bars} bars, {source.kit} kit');return
            if Path(args.output).suffix.lower()=='.mid':target=export_drum_midi(source,args.output)
            else:target=export_drum_audio(source,args.output)
        print('Created:',target);return
    src=Path(args.score).read_text(encoding='utf-8')
    score=parse_text(src,strict=True)
    if args.command=='validate':
        print(f'OK: {len(score.measures)} bars, {score.numerator}/{score.denominator}, BPM {score.bpm}')
        return
    suffix=Path(args.output).suffix.lower()
    if suffix=='.mid': target=export_midi(score,args.output,args.instrument)
    elif suffix in ('.wav','.mp3'): target=export_audio(score,args.output,args.instrument,args.sf2)
    elif suffix=='.png': target=export_png(score,args.output,args.bars_per_row)
    else: p.error('Output must end in .mid, .wav, .mp3, or .png')
    print('Created:',target)

if __name__ == '__main__':main()
