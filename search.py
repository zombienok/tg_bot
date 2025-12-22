# search.py
import spacy
import wikipedia

nlp = spacy.load("en_core_web_sm")
wikipedia.set_lang("en")

def extract_keyphrase(doc):
    for token in doc:
        if token.dep_ == "pobj":
            tokens = [left for left in token.lefts if left.dep_ in ("amod", "compound")]
            tokens.append(token)
            for child in token.rights:
                if child.dep_ == "prep":
                    tokens.append(child)
                    for gc in child.children:
                        if gc.dep_ == "pobj":
                            tokens.extend([gcl for gcl in gc.lefts if gcl.dep_ in ("amod", "compound")] + [gc])
            if tokens:
                return " ".join(t.text for t in sorted(tokens, key=lambda x: x.i))
    verbs = [t for t in reversed(doc) if t.pos_ == "VERB"]
    for verb in verbs:
        subj = next((c for c in verb.children if c.dep_ == "nsubj"), None)
        if subj:
            subj_part = [left for left in subj.lefts if left.dep_ in ("amod", "compound")]
            subj_part.append(subj)
            phrase = " ".join(t.text for t in sorted(subj_part, key=lambda x: x.i)) + " " + verb.lemma_
            dobj = next((c for c in verb.children if c.dep_ == "dobj"), None)
            if dobj:
                dobj_part = [left for left in dobj.lefts if left.dep_ in ("amod", "compound")]
                dobj_part.append(dobj)
                phrase += " " + " ".join(t.text for t in sorted(dobj_part, key=lambda x: x.i))
            return phrase.strip()
    return " ".join(t.text for t in doc if t.pos_ in ("NOUN", "PROPN", "VERB")) or str(doc)

def search_wikipedia(query: str) -> str:
    try:
        return wikipedia.summary(query, sentences=1)
    except wikipedia.exceptions.DisambiguationError as e:
        return wikipedia.summary(e.options[0], sentences=1) if e.options else f"Too many meanings for '{query}'."
    except wikipedia.exceptions.PageError:
        return f"Nothing found about '{query}' in Wikipedia."
    except Exception:
        return "Sorry, Wikipedia search failed."