class PromptBuilder:
    def build(self, context: str, question: str):
        return f"Context:\n{context}\n\nUser question:\n{question}"
