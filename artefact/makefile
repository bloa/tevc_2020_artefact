all:
	python3 automate_tevc.py --context tmp --step training --run
	python3 automate_tevc.py --context tmp --step validation --run
	python3 automate_tevc.py --context tmp --step test --run
	python3 automate_tevc.py --context tmp --step assess-gp-test --run
	python3 automate_tevc.py --context tmp --step assess-gi-all --run
	python3 automate_tevc.py --context tmp --step assess-gp-all --run

analyse:
	python3 automate_tevc.py --context tmp --step analyse --run
