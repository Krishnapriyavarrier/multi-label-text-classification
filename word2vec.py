import math
import tensorflow as tf


class Word2Vec():
    """
    model for word2vec
    can be used network embedding as well

    Args:

    num_sampled: int, number of negative examples to sample
    vocabulary_size: int
    embedding_size: int
    """

    def __init__(self,
                 num_sampled,
                 vocabulary_size,
                 embedding_size,
                 embedding_value=None,
                 nce_W_value=None,
                 nce_b_value=None):

        self.vocabulary_size, self.embedding_size = (vocabulary_size,
                                                     embedding_size)
        assert self.vocabulary_size > 0
        assert self.embedding_size > 0

        # Input data.
        self.train_inputs = tf.placeholder(tf.int32, shape=None, name='input_x')
        self.train_labels = tf.placeholder(tf.int32, shape=[None, 1], name='input_y')

        # Ops and variables pinned to the CPU because of missing GPU implementation
        with tf.device('/cpu:0'):
            # Look up self.embeddings for inputs.
            with tf.name_scope('embedding'):
                if embedding_value is None:
                    embedding_value = tf.random_uniform(
                        [self.vocabulary_size, self.embedding_size], -1.0, 1.0)
                else:
                    assert (self.vocabulary_size, self.embedding_size) == \
                        embedding_value.shape, 'shape does not match'

                self.embeddings = tf.Variable(
                    embedding_value,
                    name='table')
                embed = tf.nn.embedding_lookup(self.embeddings, self.train_inputs, name='looked-up-value')

            with tf.name_scope('nce'):
                # Construct the variables for the NCE loss
                if nce_W_value is None:
                    nce_W_value = tf.truncated_normal([self.vocabulary_size, self.embedding_size],
                                                      stddev=1.0 / math.sqrt(self.embedding_size))
                self.nce_weights = tf.Variable(nce_W_value)

                if nce_b_value is None:
                    nce_b_value = tf.zeros([self.vocabulary_size])
                self.nce_biases = tf.Variable(nce_b_value)

        # Compute the average NCE loss for the batch.
        # tf.nce_loss automatically draws a new sample of the negative labels each
        # time we evaluate the loss.
        with tf.name_scope('loss'):
            self.loss = tf.reduce_mean(
                tf.nn.nce_loss(weights=self.nce_weights,
                               biases=self.nce_biases,
                               labels=self.train_labels,
                               inputs=embed,
                               num_sampled=num_sampled,
                               num_classes=self.vocabulary_size))

        norm = tf.sqrt(tf.reduce_sum(tf.square(self.embeddings), 1, keep_dims=True))
        self.normalized_embeddings = self.embeddings / norm
