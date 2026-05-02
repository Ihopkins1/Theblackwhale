from pathlib import Path
import runpy

# Run the Orca generator from the templates folder so the root-level command works.
script_path = Path(__file__).with_name('templates').joinpath('orca_loading.py')
runpy.run_path(script_path, run_name='__main__')
