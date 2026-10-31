.PHONY: all check clean

all: proposal.pdf

proposal.pdf: progress.md report-template.tex repo-links.lua ../scripts/build_progress_report.py
	python ../scripts/build_progress_report.py

check:
	python ../scripts/build_progress_report.py --check

clean:
	python -c "print('No compiler products are stored in proposal/.')"
