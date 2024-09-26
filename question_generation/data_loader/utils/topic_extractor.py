from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


class TopicExtractor:
    def __init__(self):
        # Load the tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(
            "ilsilfverskiold/tech-keywords-extractor"
        )
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            "ilsilfverskiold/tech-keywords-extractor"
        )

    def extract_keywords(self, paragraph):
        # Prepare the input data by encoding
        inputs = self.tokenizer.encode(
            "extract keywords: " + paragraph, return_tensors="pt", truncation=True
        )

        # Perform inference (generate keywords)
        outputs = self.model.generate(inputs)
        print("output==-=-=-=-=-", outputs)
        # Decode the output
        keywords = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        print("keywords=-=-=-=-=-", keywords)

        return keywords
