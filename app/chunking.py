def chunk_text(text: str, chunk_size: int = 500) -> list:
  """
  Splits text into chunks of approx. 'chunk_size' characters.
  """
  chunks = []
  current_chunk = ''
  words = text.split()

  for word in words:
    #Check if adding the word exceeds chunk size
    if len(current_chunk) + len(word) + 1 <= chunk_size:
      current_chunk += (word + ' ')
    else:
      # Store current chunk and start new one
      chunks.append(current_chunk.strip())
      current_chunk = word + ' '

  # Add the last chunk if not empty
  if current_chunk:
      chunks.append(current_chunk.strip())

  return chunks

def chunk_pdf_pages(pages_and_texts: list, chunk_size: int = 500) -> list[dict]:
  """
  Takes PDF pages with text and splits them into chunks

  Returns a list of dicts with page_number, chunk_index, and chunk_text.
  """
  all_chunks = []
  for page in pages_and_texts:
    page_number = page["page_number"]
    page_text = page["page_text"]

    chunks = chunk_text(page_text, chunk_size = chunk_size)
    for i, chunk in enumerate(chunks):
      all_chunks.append({
          "page_number": page_number,
          "chunk_index": i,
          "chunk_char_count": len(chunk),
          "chunk_word_count": len(chunk.split()),
          "chunk_token_count": len(chunk) / 4, # 1 token = ~4 chars
          "chunk_text": chunk
      })

  return all_chunks

#Example usage 
#chunked_pages = chunk_pdf_pages(pages_and_texts, chunk_size=500)
#print(f"Total chunks: {len(chunked_pages)}")
#print(f"First chunk (page {chunked_pages[0]['page_number']}): {chunked_pages[0]['chunk_text'][:200]}")