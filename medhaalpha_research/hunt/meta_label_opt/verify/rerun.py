# Re-run the tester's run.py unchanged, but redirect its results.json into verify/ so the tester's files are untouched.
import sys
sys.dont_write_bytecode = True
SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt/meta_label_opt')
import run
run.OUT = SP + '/hunt/meta_label_opt/verify'
run.main()
