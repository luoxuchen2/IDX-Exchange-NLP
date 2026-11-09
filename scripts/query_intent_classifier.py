import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

class QueryIntentClassifier:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            ngram_range=(1, 2)
        )
        self.model = LogisticRegression(
            max_iter=1000,
            random_state=42
        )

    def train(self, queries, labels):
        X = self.vectorizer.fit_transform(queries)
        self.model.fit(X, labels)

    def predict(self, query):
        X = self.vectorizer.transform([query])
        probas = self.model.predict_proba(X)[0]

        index = np.argmax(probas)
        intent = self.model.classes_[index]
        confidence = float(probas[index])

        return intent, confidence

    def predict_detailed(self, query):
        X = self.vectorizer.transform([query])
        probas = self.model.predict_proba(X)[0]

        return {
            "query": query,
            "intent": self.model.classes_[np.argmax(probas)],
            "confidence": float(np.max(probas)),
            "probabilities": {
                label: float(prob)
                for label, prob in zip(self.model.classes_, probas)
            }
        }
