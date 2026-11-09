"""
Smoke test: PsychoPy + pylink + EyeLinkCoreGraphicsPsychoPy (unchanged).

Run without hardware:
  python eyelink_smoke_test.py

Try real EyeLink connection (may fail without tracker):
  python eyelink_smoke_test.py --eyelink

Exit code 0 if imports and window succeed; prints PsychoPy version.
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--eyelink",
        action="store_true",
        help="Attempt pylink.EyeLink() connect (requires host / tracker)",
    )
    args = parser.parse_args()

    try:
        import psychopy
        print(f"PsychoPy version: {psychopy.__version__}")
    except Exception as e:
        print(f"FAIL: import psychopy: {e}", file=sys.stderr)
        return 1

    try:
        import pylink  # noqa: F401
    except Exception as e:
        print(f"FAIL: import pylink: {e}", file=sys.stderr)
        return 1

    try:
        from EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy  # noqa: F401
    except Exception as e:
        print(f"FAIL: import EyeLinkCoreGraphicsPsychoPy: {e}", file=sys.stderr)
        return 1

    try:
        from psychopy import visual, core

        win = visual.Window(
            size=(1280, 768),
            fullscr=False,
            color="gray",
            units="pix",
        )
        win.flip()
        win.close()
        core.quit()
    except Exception as e:
        print(f"FAIL: Window open/close: {e}", file=sys.stderr)
        return 1

    if args.eyelink:
        try:
            el = pylink.EyeLink()
            print("EyeLink: connected (basic open). Closing...")
            el.close()
        except Exception as e:
            print(
                f"NOTE: EyeLink connect failed (expected without host): {e}",
                file=sys.stderr,
            )
            return 2

    print("OK: smoke test passed (imports + Window + EyeLinkCoreGraphics import).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
