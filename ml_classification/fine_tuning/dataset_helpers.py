import torch
from torch.utils.data import Dataset


# ---------- Chunking ----------
def chunk_text(tokenizer, text, max_tokens, stride):
    tokens = tokenizer(text, add_special_tokens=False)["input_ids"]
    chunks = []
    for i in range(0, len(tokens), max_tokens - stride):
        chunk_ids = tokens[i : i + max_tokens]
        chunks.append(tokenizer.decode(chunk_ids))
    return chunks


class PDFChunkDataset(Dataset):
    def __init__(
        self,
        pdf_texts,
        pdf_labels,
        tokenizer,
        max_seq_len=None,
        chunking: bool = False,
        chunking_max_seq_len: int = 256,
        chunking_stride: int = 10,
    ):
        self.samples = []
        self.tokenizer = tokenizer
        self.chunking = chunking
        self.max_seq_len = max_seq_len
        self.chunking_max_seq_len = chunking_max_seq_len
        self.chunking_stride = chunking_stride

        for text, label in zip(pdf_texts, pdf_labels):
            if self.chunking:
                chunks = chunk_text(
                    tokenizer,
                    text,
                    max_tokens=self.chunking_max_seq_len,
                    stride=self.chunking_stride,
                )
                for ch in chunks:
                    self.samples.append((ch, label))
            else:
                self.samples.append((text, label))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        text, label = self.samples[idx]
        enc = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_seq_len,
            return_tensors="pt",
        )
        item = {k: v.squeeze(0) for k, v in enc.items()}
        item["labels"] = torch.tensor(label, dtype=torch.long)
        return item
