### Algorithm explanation:
The algorithm used is cosine similarity, which compares vectors for similarity.

###  Judgment Criteria Explanation:
The core idea is:
if two sentences express the same meaning (even with different wording), they should have similar semantic embeddings in vector space.

we use SBERT model (specifically paraphrase-MiniLM-L6-v2) to transform each sentence into an embedding vector.
then, we compute how close these vectors are using cosine similarity.

if the similarity exceeds a defined threshold (e.g., 0.8), the sentences are labeled "ENTAIL", otherwise "NO_ENTAIL".

### 3 Ideas Future Improvements:
1. Average similarity: combine results from different models to get the average similarity.
2. Adaptive threshold: instead of using a fixed threshold, implement adaptive threshold, where the threshold dynamically adjusts based on linguistic or a sentence length.
3. Domain specific fine-tuning: we can train the model with domain specific examples, using the sentences we saved, or other examples, it would improve the accuracy 