# train_intent_model.py
# This file trains the machine learning model for intent classification

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import pickle
import re


class IntentModelTrainer:
    """
    Trains a machine learning model to classify user intents
    """

    def __init__(self, dataset_path):
        """
        Initialize the trainer

        dataset_path: path to the training dataset file
        """
        self.dataset_path = dataset_path
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            max_features=1000,
            ngram_range=(1, 2)  # Use single words and two-word combinations
        )
        self.model = LogisticRegression(max_iter=1000)
        self.data = None

    def load_data(self):
        """
        Load the training dataset from file
        """
        print("Loading training data...")

        # Read the CSV file
        self.data = pd.read_csv(self.dataset_path)

        # Clean the text column (remove quotes if present)
        self.data['text'] = self.data['text'].str.strip('"')

        print(f"Loaded {len(self.data)} training examples")
        print(f"Intents found: {self.data['intent'].unique()}")
        print()

    def preprocess_text(self, text):
        """
        Clean and prepare text for training

        text: the input text to clean
        Returns: cleaned text
        """
        # Convert to lowercase
        text = text.lower()

        # Remove extra spaces
        text = ' '.join(text.split())

        return text

    def prepare_data(self):
        """
        Prepare the data for training
        """
        print("Preparing data for training...")

        # Clean all text
        self.data['text'] = self.data['text'].apply(self.preprocess_text)

        # Split into features (X) and labels (y)
        X = self.data['text']
        y = self.data['intent']

        # Split into training and testing sets (80% train, 20% test)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        print(f"Training set: {len(X_train)} examples")
        print(f"Testing set: {len(X_test)} examples")
        print()

        return X_train, X_test, y_train, y_test

    def train_model(self, X_train, y_train):
        """
        Train the machine learning model
        """
        print("Training the model...")

        # Convert text to numerical features using TF-IDF
        X_train_vectors = self.vectorizer.fit_transform(X_train)

        # Train the logistic regression model
        self.model.fit(X_train_vectors, y_train)

        print("Model training complete!")
        print()

    def evaluate_model(self, X_test, y_test):
        """
        Test the model accuracy
        """
        print("Evaluating model performance...")

        # Convert test text to vectors
        X_test_vectors = self.vectorizer.transform(X_test)

        # Make predictions
        y_pred = self.model.predict(X_test_vectors)

        # Calculate accuracy
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Model Accuracy: {accuracy * 100:.2f}%")
        print()

        # Show detailed report
        print("Detailed Performance Report:")
        print(classification_report(y_test, y_pred))

    def save_model(self, model_path='intent_model.pkl', vectorizer_path='vectorizer.pkl'):
        """
        Save the trained model and vectorizer to files
        """
        print("Saving model...")

        # Save the model
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)

        # Save the vectorizer
        with open(vectorizer_path, 'wb') as f:
            pickle.dump(self.vectorizer, f)

        print(f"Model saved to {model_path}")
        print(f"Vectorizer saved to {vectorizer_path}")
        print()

    def test_predictions(self):
        """
        Test the model with some example sentences
        """
        print("Testing with example sentences...")
        print("-" * 50)

        test_examples = [
            "I just took my medication",
            "Can you remind me in 30 minutes?",
            "I'm skipping today's dose",
            "When did I last take my meds?",
            "How am I doing this week?",
            "Change my medication time to 8pm",
            "Add a new medication",
            "Hey thanks"
        ]

        for example in test_examples:
            # Prepare the text
            cleaned = self.preprocess_text(example)

            # Convert to vector
            vector = self.vectorizer.transform([cleaned])

            # Predict intent
            predicted_intent = self.model.predict(vector)[0]

            # Get confidence scores
            probabilities = self.model.predict_proba(vector)[0]
            confidence = max(probabilities) * 100

            print(f"Text: '{example}'")
            print(f"Predicted Intent: {predicted_intent}")
            print(f"Confidence: {confidence:.1f}%")
            print()

    def run_training(self):
        """
        Run the complete training process
        """
        print("=" * 60)
        print("INTENT CLASSIFICATION MODEL TRAINING")
        print("=" * 60)
        print()

        # Step 1: Load data
        self.load_data()

        # Step 2: Prepare data
        X_train, X_test, y_train, y_test = self.prepare_data()

        # Step 3: Train model
        self.train_model(X_train, y_train)

        # Step 4: Evaluate model
        self.evaluate_model(X_test, y_test)

        # Step 5: Save model
        self.save_model()

        # Step 6: Test with examples
        self.test_predictions()

        print("=" * 60)
        print("Training Complete! ✅")
        print("=" * 60)


def main():
    """
    Main function to run the training
    """
    # Path to your training dataset
    dataset_path = 'training_dataset.csv'

    # Create trainer
    trainer = IntentModelTrainer(dataset_path)

    # Run the training process
    trainer.run_training()


if __name__ == "__main__":
    main()