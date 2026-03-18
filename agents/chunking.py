import re
import voyageai
from src.config import settings


client = voyageai.Client(settings.settings.voyage_key)


# sample

DOCUMENT = """ 

# Mission to Mars: Past, Present, and Future

### Introduction
Humanity's fascination with Mars, the fourth planet from the Sun, spans centuries. Often called the "Red Planet" due to the iron oxide prevalent on its surface, Mars is a terrestrial planet with a thin atmosphere. It holds the solar system's largest volcano, Olympus Mons, and a massive canyon system known as Valles Marineris. 

### The Era of Early Exploration
The journey to understand Mars began with flybys in the 1960s. Mariner 4, launched by NASA in 1964, was the first successful flyby, returning the first close-up photographs of another planet. These grainy, black-and-white images shattered the illusion of a lush, inhabited world, revealing instead a barren, cratered landscape. Following the flybys, the Viking program in the 1970s marked a monumental leap forward; Viking 1 and Viking 2 successfully landed on the Martian surface, conducting the first on-site biological experiments designed to search for signs of microscopic life in the soil. Although the results were largely considered inconclusive, they laid the essential groundwork for all future rovers and landers.

### Modern Rovers and Discoveries
In the 21st century, the strategy shifted to "follow the water." Several highly sophisticated rovers have been deployed to the surface:
* **Spirit and Opportunity (2004):** Twin rovers that found conclusive geological evidence that liquid water once flowed on Mars.
* **Curiosity (2012):** A car-sized rover equipped with a chemistry lab, which determined that Mars once had the chemical ingredients required to support microbial life.
* **Perseverance (2021):** The most advanced rover to date, tasked with caching rock samples for a future return mission and deploying the Ingenuity helicopter—the first aircraft to achieve powered, controlled flight on another planet.

### The Challenges of Human Colonization
Looking ahead, the ultimate goal of several space agencies and private aerospace companies is establishing a permanent human settlement on Mars. However, the logistical and biological challenges are immense. The journey alone takes about seven months, exposing astronauts to high levels of cosmic radiation and microgravity. Once on the surface, colonists would have to survive an environment where the average temperature is -81 degrees Fahrenheit (-62 degrees Celsius) and the atmosphere is 95% carbon dioxide.

Furthermore, generating breathable air, sourcing liquid water, and growing food in toxic, perchlorate-rich soil will require cutting-edge technological innovations. Despite these massive hurdles, the dream of becoming a multi-planetary species continues to drive relentless engineering and scientific progress.

"""


# chunking:
def chunk_by_char(text, chunk_size=150, chunk_overlap=20):
    chunks = []
    start_idx = 0

    while start_idx < len(text):
        end_idx = min(start_idx + chunk_size, len(text))
        chunks.append(text[start_idx:end_idx])
        start_idx = end_idx - chunk_overlap if end_idx < len(text) else len(text)

    return chunks


def chunk_by_sentence(text, max_sentences_per_chunk=3, overlap_sentences=1):
    sentences = re.split(r"(?<=[.!?])\s", text.strip())
    chunks = []
    start_idx = 0

    while start_idx < len(sentences):
        end_idx = min(start_idx + max_sentences_per_chunk, len(text))
        chunks.append(" ".join(sentences[start_idx:end_idx]))
        start_idx += max_sentences_per_chunk - overlap_sentences
        if start_idx < 0:
            start_idx = 0

    return chunks


def chunk_by_section(document_text):
    return [s.strip() for s in re.split(r"\n##", document_text) if s.strip()]


# embedding
def embed(texts: list[str], model: str = "voyage-4") -> list[list[float]]:
    # return embedding vector per text
    # voyage-4 -> 2048 dimensions
    # voyage-3-lite -> 512 dimensions
    # voyage-3 -> 1024 dimensions
    result = client.embed(texts, model=model, output_dimension=2048)  #!!
    return result.embeddings


def log_chunks(chunks: list[str], embeddings: list[list[float]]) -> None:
    for i, chunk in enumerate[str](chunks):
        print(f"Chunk {i + 1}:")
        print(f"Embedding: {embeddings[i][:5]}:")
        print("-" * 60)
        print(chunk)
        print("-" * 60)
        print("\n")


def main():
    print("Document length:", len(DOCUMENT), "characters")

    chunks = chunk_by_char(DOCUMENT, chunk_size=150, chunk_overlap=20)
    chunks = chunk_by_sentence(DOCUMENT, max_sentences_per_chunk=3, overlap_sentences=1)
    chunks = chunk_by_section(DOCUMENT)
    embeddings = embed(chunks[:3])

    log_chunks(chunks[:3], embeddings)


if __name__ == "__main__":
    main()
