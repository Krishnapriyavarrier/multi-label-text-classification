# coding: utf-8

import os
import numpy as np
import tensorflow as tf

from tensorflow.contrib import learn
from tqdm import tqdm

from data_helpers import load_pickle, batch_iter
from eval_helpers import precision_at_ks


tf.flags.DEFINE_string('data_dir', '', 'directory of dataset')
tf.flags.DEFINE_boolean('use_node_embedding', False, 'use node embedding or not')

tf.flags.DEFINE_string("checkpoint_dir", "",
                       "Checkpoint directory from training run")
tf.flags.DEFINE_integer("batch_size", 64, "")

tf.flags.DEFINE_boolean("allow_soft_placement", True, "Allow device soft device placement")
tf.flags.DEFINE_boolean("log_device_placement", False, "Log placement of ops on devices")

FLAGS = tf.flags.FLAGS
FLAGS._parse_flags()
print("\nParameters:")
for attr, value in sorted(FLAGS.__flags.items()):
    print("{}={}".format(attr.upper(), value))
print("")

data_dir = FLAGS.data_dir

_, _, test_text = load_pickle(
    os.path.join(data_dir, "text_split.pkl"))
_, _, y_id_test = load_pickle(
    os.path.join(data_dir, "labels_id_split.pkl"))

_, _, node_ids_test = load_pickle(
    os.path.join(data_dir, "node_ids_split.pkl"))


vocab_path = os.path.join(data_dir, "vocab")
vocab_processor = learn.preprocessing.VocabularyProcessor.restore(vocab_path)

X = vocab_processor.transform(test_text)

checkpoint_file = tf.train.latest_checkpoint(FLAGS.checkpoint_dir)

graph = tf.Graph()
with graph.as_default():
    session_conf = tf.ConfigProto(
        allow_soft_placement=FLAGS.allow_soft_placement,
        log_device_placement=FLAGS.log_device_placement
    )
    sess = tf.Session(config=session_conf)
    with sess.as_default():
        # Load the saved meta graph and restore variables
        saver = tf.train.import_meta_graph("{}.meta".format(checkpoint_file))
        saver.restore(sess, checkpoint_file)

        if FLAGS.use_node_embedding:
            input_x = graph.get_operation_by_name("kim_cnn/input_x").outputs[0]
            dropout_keep_prob = graph.get_operation_by_name("kim_cnn/dropout_keep_prob").outputs[0]
            input_node_ids = graph.get_operation_by_name("combined/input_node_ids").outputs[0]

            label_scores = graph.get_operation_by_name("combined/output/scores").outputs[0]
        else:
            input_x = graph.get_operation_by_name("input_x").outputs[0]
            dropout_keep_prob = graph.get_operation_by_name("dropout_keep_prob").outputs[0]
            
            label_scores = graph.get_operation_by_name("output/scores").outputs[0]
    
        # Generate batches for one epoch
        if FLAGS.use_node_embedding:
            input_data = list(zip(list(X), list(node_ids_test)))
        else:
            input_data = list(X)
        batches = batch_iter(input_data, FLAGS.batch_size, 1, shuffle=False)

        # Collect the predictions here
        all_label_scores = None
        for x_test_batch in tqdm(batches):
            if FLAGS.use_node_embedding:
                text_batch, node_ids_batch = zip(*x_test_batch)
                label_score_values = sess.run(
                    label_scores,
                    {input_x: text_batch, input_node_ids: node_ids_batch, dropout_keep_prob: 1.0})
            else:
                label_score_values = sess.run(
                    label_scores, {input_x: x_test_batch, dropout_keep_prob: 1.0})

            if all_label_scores is not None:
                all_label_scores = np.concatenate([all_label_scores, label_score_values])
            else:
                all_label_scores = label_score_values

        precisions = precision_at_ks(all_label_scores, y_id_test, ks=[1, 3, 5])

    for k, p in zip([1, 3, 5], precisions):
        print('p@{}: {:.5f}'.format(k, p))
