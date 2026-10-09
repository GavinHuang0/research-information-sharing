.PHONY: all clean

all: proposal.pdf

# Use standard TeX Live tools; BibTeX resolves the standalone bibliography.
proposal.pdf: proposal.tex references.bib
	pdflatex -interaction=nonstopmode -halt-on-error proposal.tex
	bibtex proposal
	pdflatex -interaction=nonstopmode -halt-on-error proposal.tex
	pdflatex -interaction=nonstopmode -halt-on-error proposal.tex

clean:
	rm -f proposal.aux proposal.bbl proposal.blg proposal.log proposal.out proposal.pdf
