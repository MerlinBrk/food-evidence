from Bio import Entrez
from xml.etree import ElementTree as ET
import textwrap

Entrez.email = "deine_mail@example.com"  # <- anpassen!

def search_pubmed(query, max_results=5):
    handle = Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=max_results,
        sort="relevance"
    )
    record = Entrez.read(handle)
    handle.close()
    return record["IdList"]  # Liste von PMIDs (Strings)

def fetch_details(pmids):
    handle = Entrez.efetch(
        db="pubmed",
        id=",".join(pmids),
        rettype="abstract",
        retmode="xml"
    )
    data = handle.read()
    handle.close()
    return data  # XML-Text

def parse_pubmed_xml(xml_data):
    """
    Gibt eine Liste von dicts mit wichtigen Infos zurück.
    """
    root = ET.fromstring(xml_data)
    papers = []

    for article in root.findall(".//PubmedArticle"):
        info = {}

        # Titel
        title_elem = article.find(".//ArticleTitle")
        info["title"] = title_elem.text if title_elem is not None else ""

        # Journal + Jahr
        journal_elem = article.find(".//Journal/Title")
        info["journal"] = journal_elem.text if journal_elem is not None else ""

        year_elem = article.find(".//JournalIssue/PubDate/Year")
        medline_date_elem = article.find(".//JournalIssue/PubDate/MedlineDate")
        if year_elem is not None:
            info["year"] = year_elem.text
        elif medline_date_elem is not None:
            info["year"] = medline_date_elem.text
        else:
            info["year"] = ""

        # Autoren
        authors = []
        for author in article.findall(".//Author"):
            last = author.findtext("LastName", default="")
            first = author.findtext("ForeName", default="")
            if last or first:
                authors.append(f"{last}, {first}")
        info["authors"] = authors

        # Abstract (alle Absätze zusammen)
        abstract_parts = []
        for ab in article.findall(".//AbstractText"):
            label = ab.get("Label")
            text = (ab.text or "").strip()
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        full_abstract = "\n".join(abstract_parts)
        info["abstract"] = full_abstract

        # PMID
        pmid_elem = article.find(".//PMID")
        info["pmid"] = pmid_elem.text if pmid_elem is not None else ""

        # DOI (falls vorhanden)
        doi = ""
        for id_elem in article.findall(".//ArticleId"):
            if id_elem.get("IdType") == "doi":
                doi = id_elem.text
                break
        info["doi"] = doi

        # sehr simple Heuristik: "Results"-Teil aus Abstract herausziehen
        info["results_snippet"] = extract_results_snippet(full_abstract)

        papers.append(info)

    return papers

def extract_results_snippet(abstract_text):
    """
    Sehr einfache Heuristik: Suche nach einem Abschnitt,
    der mit 'Results' oder 'Result:' beginnt.
    """
    if not abstract_text:
        return ""

    lower = abstract_text.lower()

    candidates = ["results:", "results ", "result:"]
    start_idx = None
    for c in candidates:
        idx = lower.find(c)
        if idx != -1:
            start_idx = idx
            break

    if start_idx is None:
        # kein expliziter Results-Tag: nimm einfach die mittleren 2–3 Sätze
        sentences = abstract_text.split(". ")
        if len(sentences) >= 3:
            middle = len(sentences) // 2
            snippet = ". ".join(sentences[middle:middle+2])
            return snippet.strip()
        return abstract_text[:400].strip()

    # ab "Results" bis etwa 400 Zeichen danach
    snippet = abstract_text[start_idx:start_idx+500]
    return snippet.strip()

def pretty_print_papers(papers):
    for i, p in enumerate(papers, start=1):
        print("=" * 80)
        print(f"[{i}] PMID: {p['pmid']}")
        print(f"Title: {p['title']}")
        print(f"Journal: {p['journal']} ({p['year']})")
        print("Authors: " + (", ".join(p['authors']) if p['authors'] else "n/a"))
        if p["doi"]:
            print(f"DOI: {p['doi']}")
        print("\nRESULTS (Snippet):")
        print(textwrap.fill(p["results_snippet"], width=80))
        print("\nFULL ABSTRACT:")
        print(textwrap.fill(p["abstract"], width=80))
        print()

if __name__ == "__main__":
    query = "covid-19 vaccine efficacy"
    pmids = search_pubmed(query, max_results=3)
    print("Gefundene PMIDs:", pmids)

    xml_data = fetch_details(pmids)
    papers = parse_pubmed_xml(xml_data)
    pretty_print_papers(papers)
