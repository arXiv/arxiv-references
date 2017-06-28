import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)

import re
import os
import datetime
import shutil
import subprocess
import numpy as np
import urllib

from typing import List, Generator

from reflink.process import util, textutil

def argmax(array):
    index, value = max(enumerate(array), key=lambda x: x[1])
    return index

def extract_tar(tarfile, destination):
    """ Extract `tarfile` to the directory `destination` """
    cmd = 'tar -xvf {} -C {}'.format(sourcetar_path, fldr)
    cmd = shlex.split(cmd)
    subprocess.check_call(cmd)

def jacard(str0, str1):
    """
    Jacard similarity score between str0 and str1, containing the fraction of
    matching words that are the same between the two strings.

    Parameters
    ----------
    str0 : str
    str1 : str

    Returns
    -------
    similarity : float
        The jacard similarity
    """
    words0 = set(str0.split())
    words1 = set(str1.split())
    shared_words = len(words0.intersection(words1))
    all_words = len(words0.union(words1))

    if all_words == 0:
        return 0.0
    return shared_words/all_words

def match_by_cost(l1, l2, cost=jacard):
    """
    Calculate the matching `ind` between l1 and l2 where l1 is similar to
    l2[ind]. That is, we return `ind` such that cost(l1 - l2[ind]) is minimized.

    Parameters
    ----------
    l1 : list of strings
    l2 : list of strings
    func : callable
        The score function to calculate distance

    Returns
    -------
    ind : list of integers
        Mapping which gives l2 closest to l1 i.e. l1 ~ l2[ind]
    """
    inds = []
    for i in l1:
        ind = argmax([cost(i, j) for j in l2])
        inds.append(ind)

    return inds

def cleaned_reference_lines(refs):
    """ Clean the raw text reference lines for better matching """
    refc = [textutil.clean_blob(unicode(r), numok=True) for r in refs]
    return remove_repeated_words(refc)

def cleaned_bib_entries(entries):
    """ Clean the raw latex source bibitems for better matching """
    bbls = []
    for entry in entries:
        entry = entry.decode('ascii', 'ignore').encode('ascii', 'ignore')
        entry = unicode(entry.strip())
        #entry = textutil.remove_latex_markup(entry) # FIXME -- uses pandoc right now
        entry = textutil.clean_blob(entry, numok=True)
        entry = entry.split()
        entry = [l for l in entry if l]
        bbls.append(' '.join(entry))
    return remove_repeated_words(bbls)

def remove_repeated_words(docs):
    """
    For purposes of comparing perhaps only partially cleaned bibitems, we remove
    words that are shared amongst all items so that they don't bias the jacard
    similarity score.

    Parameters
    ----------
    docs : list of str
    
    Returns
    -------
    modified_docs : list of str
        Strings with common words removed
    """
    # get a list of common words
    common = None
    for doc in docs:
        if common is None:
            common = set(doc.split())
        else:
            common.intersection_update(set(doc.split()))

    # remove the words from the strings
    newdocs = []
    for doc in docs:
        newdoc = ' '.join([
            w for w in doc.split() if w not in common
        ])
        newdocs.append(newdoc)
    return newdocs

def tex_escape(text: str) -> str:
    """
    Prepare symbols common to latex to be included in a URL. Uses sphinx list
    of tex replacements to escape raw latex for use in \\url directives.
    """
    return text.translate(texconversions.tex_escape_map)

# regex which are used to extract bibliographies
DEFAULT_HEAD = re.compile(r'(\\begin{thebibliography}(\{.*\})?)')
DEFAULT_TAIL = re.compile(r'(\\end{thebibliography}(\{.*\})?)')
DEFAULT_MARKER = re.compile(r'\\bibitem[^a-zA-Z0-9]')
LATEX_COMMENT = re.compile(r'(^|.*[^\\])(\%.*$)')

def extract_bibs(text: str) -> Generator[str, None, None]:
    """
    Generator which yields bibliography sections from a file by identifying
    latex sections between \\begin and \\end of `thebibliography`.

    Parameters
    ----------
    text : str
        The full text from which to extract bibliographies, perhaps the 
        contents of a bbl or tex file.

    Returns
    -------
    bibliographies : generator[str]
        Each individual bibliography
    """
    head = DEFAULT_HEAD.finditer(txt)
    tail = DEFAULT_TAIL.finditer(txt)

    for h,t in zip(head, tail):
        yield txt[h.end():t.start()].strip()

def replace_bibs(text: str, replacements: List[str]) -> str:
    """
    Replace the bibliographies in `text` with the corresponding reformatted
    sections `replacements`. Since we didn't store the locations of the bibs
    when we extracted them, follow the same method to re-inject them.
    """
    out = ''
    head = DEFAULT_HEAD.finditer(text)
    tail = DEFAULT_TAIL.finditer(text)

    lh = lt = None
    for i,(h,t) in enumerate(zip(head, tail)):
        if not lh:
            out += txt[:h.end()]+'\n'
        else:
            out += txt[lt.start():h.end()]+'\n'
        out += replacements[i]+'\n'
        lh = h
        lt = t

    out += txt[lt.start():]+'\n'
    return out

def bib_items_head(bibliography: str, marker=DEFAULT_MARKER) -> str:
    """
    Return the header of the bibliography (the stuff that precedes actual
    \\bibitems, the individual references)

    Parameters
    ----------
    bibliography : str
        Full text of a bibliography section from `begin` to `end`

    marker : re.compile
        Regex which denotes the beginning of an individual reference,
        default is \\bibitem (DEFAULT_MARKER)

    Returns
    -------
    head : str
        The header of the bibliography
    """
    head = ''
    initem = False

    contents = bibliography.split('\n')
    for line in contents:
        match = marker.search(line)
        if match:
            head += '{}\n'.format(line[:match.start()])
            return head
        else:
            head += '{}\n'.format(line)


def bib_items_iter(bibliography: str, marker=DEFAULT_MARKER) -> Generator[str, None, None]:
    """
    Generator which yields each individual reference from a raw bibliography
    text.  These elements are typically denoted by \\bibitem (though I'm not
    100% sure this is always the case TBD)

    Parameters
    ----------
    bibliography : str
        Full raw text of bibliography section

    marker : re.compile
        Regex which denotes the beginning of an individual reference
        default is \\bibitem (DEFAULT_MARKER)

    Returns
    -------
    bibitems : generator
        Generator of text of each reference
    """
    curbbl = ''
    initem = False

    contents = bibliography.split('\n')
    for line in contents:
        line = LATEX_COMMENT.sub(r'\1', line)

        match = marker.search(line)
        if match:
            ind = match.start()

            if initem:
                curbbl += '{}\n'.format(line[:ind])
                yield curbbl

            curbbl = '{}\n'.format(line[ind:])
            initem = True
        elif initem:
            curbbl += '{}\n'.format(line)
        else:
            continue

def url_formatter_arxiv(reference_line: str, baseurl: str='https://arxiv.org/lookup',
        queryparam: str='q', marker: str='GO') -> str:
    """
    Create the latex for a URL given a `reference_line`. In the process, does
    basic encoding so that latex characters work in the URL and is urlencoded
    """
    refline = refline.encode('ascii', 'ignore')
    query = tex_escape(urllib.urlencode({'q': refline}))
    url = '{}?{}'.format(baseurl, query)

    return '\href{{{url}}}{marker}\n\n'.format(
        entry=entry.strip(), url=url, marker=marker
    )


def bbl_inject_urls(txt: str, references: List[str],
        formatter=url_formatter_arxiv) -> List[str]:
    """
    Given a particular bibliography (begin...end segment), inject each bibitem
    with URLs from a list of references and return the section again, but
    modified as raw text.

    Parameters
    ----------
    txt : str
        Raw text of a bibliography to be modified with URLs

    references : list of str
        Reference lines which are used for matching and URL formation

    formatter : callable
        Formatter function which takes a reference_line and returns a latex URL

    Returns
    -------
    bibliography : str
        Raw text for a replacement bibliography with URLs injected
    """
    def _inject(entry, refline):
        return '{entry}\n{url}'.format(entry, formatter(refline))

    replacement_bbls = []

    for bbl in extract_bibs(txt):
        head = bib_items_head(bbl)
        bibitems = list(bib_items_iter(bbl))
        inds = match_by_cost(
            cleaned_bib_entries(bibitems),
            cleaned_reference_lines(references)
        )

        out = []
        for i, (ind, entry) in enumerate(zip(inds, bibitems)):
            # skip the injection for bibitems which already have URLs
            if 'url' in bibitems[i] or 'href' in bibitems[i]:
                out.append(entry)
                continue
            entry = _inject(entry, references[ind])
            out.append(entry)
        replacement_bbls.append('{}\n\n{}'.format(head, '\n'.join(out)))

    return replace_bibs(txt, replacement_bbls)

def transform_bbl(filename: str, reference_lines: List[str]):
    """
    Take a .bbl/.tex filename and a set of reference lines, save the filename
    to a backup and rewrite with links in the bibliography section.
    """
    util.backup(filename)

    with open(filename) as f:
        out = bbl_inject_urls(f.read(), refs)

    with open(filename, 'w') as f:
        f.write(out)

def run_autotex(directory: str) -> str:
    """
    Run the AutoTeX docker image on the directory `fldr`.

    Parameters
    ----------
    directory : str
        Host directory containing latex source to compile

    Returns
    -------
    output : str
        Filename of the final output created by the AutoTeX process
    """
    # FIXME -- this process will likely be greatly simplified by the newest AutoTeX
    # FIXME -- also, magic docker image names appearing again
    def _find(e):
        f = files_modified_since(directory, timestamp, extension=e)
        if f:
            return os.path.join(directory, f)
        return None

    timestamp = datetime.datetime.now()
    run_docker('mattbierbaum/autotex:v0.906.0-1', {directory: '/autotex'}, 'go')

    pdf, dvi, ps = [_find(e) for e in ['pdf', 'dvi', 'ps']]
    if pdf:
        return pdf
    if ps:
        with util.indir(directory):
            ps2pdf(ps)
        return _find('pdf')
    if dvi:
        with util.indir(directory):
            dvi2ps(dvi)
            ps = _find('ps')
            ps2pdf(ps)
        return _find('pdf')

    raise Exception("No output found for autotex")

def modify_source_with_urls(source_path: str, reference_lines: List[str]) -> None:
    """
    Perform the URL injection into latex source (both .tex, .bbl) and modify
    files in place, making backups before doing so.

    Parameters
    ----------
    source_directory : str
        The root directory in which to search for tex and bbl files
        and to run autotex

    reference_lines : list of str
        The references to match and inject into the list
    """
    join = os.path.join

    files = (
        glob.glob(join(join(source_path, "**"), "*.tex"), recursive=True) +
        glob.glob(join(join(source_path, "**"), "*.bbl"), recursive=True)
    )
    for fn in files:
        transform_bbl(fn, reference_lines)

def inject_urls(pdf_path: str, source_path: str, metadata: dict,
        cleanup: bool=True) -> str:
    """
    Given a tarfile of latex source, inject references, and build a new pdf.

    Parameters
    ----------
    pdf_path : str
        Local filepath for the pdf being modified

    source_path : str
        Location of the source tarfile that will be injected

    metadata : dict
        Metadata extracted from the PDF by other processes (see schema)

    Returns
    -------
    modified_pdf_path : str
        Location of the modified pdf
    """
    source_path = os.path.abspath(source_path)

    # extract the relevant information from the metadata
    reference_lines = []
    for reference in metadata.get('references', []):
        if 'raw' in reference.ref['raw']:
            reference_lines.append(reference['raw'])

    # do the transformation in a temporary directory
    with tempdir(cleanup=cleanup) as fldr:
        extract_tar(source_path, fldr)

        os.chmod(fldr, 0o775)
        modify_source_with_urls(fldr, reference_lines)
        pdf = run_autotex(fldr)
        return pdf

