import json
import os
import socket
from io import BytesIO
import numpy as np
import PIL.Image
import tensorflow as tf
import tensorflow_hub as hub
from scipy.stats import truncnorm
from flask import Flask, request, send_file
from flask_cors import CORS
from redis import Redis, RedisError

app = Flask(__name__)
CORS(app)

# Initialize the module
filepath = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(filepath, 'tf_hub_dir')

os.environ["TFHUB_CACHE_DIR"] = filepath
module_path = 'https://tfhub.dev/deepmind/biggan-256/2'

tf.reset_default_graph()
module = hub.Module(module_path)

inputs = {k: tf.placeholder(v.dtype, v.get_shape().as_list(), k)
          for k, v in module.get_input_info_dict().items()}
output = module(inputs)
print("start3")

input_z = inputs['z']
input_y = inputs['y']
input_trunc = inputs['truncation']

dim_z = input_z.shape.as_list()[1]
vocab_size = input_y.shape.as_list()[1]

# Set up helper functions
def truncated_z_sample(batch_size, truncation=1., seed=None):
  state = None if seed is None else np.random.RandomState(seed)
  values = truncnorm.rvs(-2, 2, size=(batch_size, dim_z), random_state=state)
  return truncation * values

def one_hot(index, vocab_size=vocab_size):
  index = np.asarray(index)
  if len(index.shape) == 0:
    index = np.asarray([index])
  assert len(index.shape) == 1
  num = index.shape[0]
  output = np.zeros((num, vocab_size), dtype=np.float32)
  output[np.arange(num), index] = 1
  return output

def one_hot_if_needed(label, vocab_size=vocab_size):
  label = np.asarray(label)
  if len(label.shape) <= 1:
    label = one_hot(label, vocab_size)
  assert len(label.shape) == 2
  return label

def sample_with_category(sess, noise, label, truncation=1., batch_size=8,
           vocab_size=vocab_size):
  noise = np.asarray(noise)
  label = np.asarray(label)
  num = noise.shape[0]
  if len(label.shape) == 0:
    label = np.asarray([label] * num)
  if label.shape[0] != num:
    raise ValueError('Got # noise samples ({}) != # label samples ({})'
                     .format(noise.shape[0], label.shape[0]))
  label = one_hot_if_needed(label, vocab_size)
  ims = []
  for batch_start in range(0, num, batch_size):
    s = slice(batch_start, min(num, batch_start + batch_size))
    feed_dict = {input_z: noise[s], input_y: label[s], input_trunc: truncation}
    ims.append(sess.run(output, feed_dict=feed_dict))
  ims = np.concatenate(ims, axis=0)
  assert ims.shape[0] == num
  ims = np.clip(((ims + 1) / 2.0) * 256, 0, 255)
  ims = np.uint8(ims)
  return ims

def sample_with_labels(sess, noise, label, truncation=1., batch_size=8,
           vocab_size=vocab_size):
  noise = np.asarray(noise)
  label = np.asarray(label)
  num = noise.shape[0]
  if label.shape[0] != num:
    raise ValueError('Got # noise samples ({}) != # label samples ({})'
                     .format(noise.shape[0], label.shape[0]))
  ims = []
  for batch_start in range(0, num, batch_size):
    s = slice(batch_start, min(num, batch_start + batch_size))
    feed_dict = {input_z: noise[s], input_y: label[s], input_trunc: truncation}
    ims.append(sess.run(output, feed_dict=feed_dict))
  ims = np.concatenate(ims, axis=0)
  assert ims.shape[0] == num
  ims = np.clip(((ims + 1) / 2.0) * 256, 0, 255)
  ims = np.uint8(ims)
  return ims

def imgrid(imarray, cols=5, pad=1):
  if imarray.dtype != np.uint8:
    raise ValueError('imgrid input imarray must be uint8')
  pad = int(pad)
  assert pad >= 0
  cols = int(cols)
  assert cols >= 1
  N, H, W, C = imarray.shape
  rows = int(np.ceil(N / float(cols)))
  batch_pad = rows * cols - N
  assert batch_pad >= 0
  post_pad = [batch_pad, pad, pad, 0]
  pad_arg = [[0, p] for p in post_pad]
  imarray = np.pad(imarray, pad_arg, 'constant', constant_values=255)
  H += pad
  W += pad
  grid = (imarray
          .reshape(rows, cols, H, W, C)
          .transpose(0, 2, 1, 3, 4)
          .reshape(rows*H, cols*W, C))
  if pad:
    grid = grid[:-pad, :-pad]
  return grid

def imbytes(array):
  array = np.asarray(array, dtype=np.uint8)
  imgBytes = BytesIO()
  PIL.Image.fromarray(array).save(imgBytes, 'jpeg')
  imgBytes.seek(0)
  return imgBytes

# Initialize TensorFlow session
initializer = tf.global_variables_initializer()

graph = tf.get_default_graph()
with graph.as_default():
    sess = tf.Session()
    sess.run(initializer)

@app.route('/category', methods=['POST'])
def generateFromCategory():
  global sess

  # Categories found here: https://gist.github.com/yrevar/942d3a0ac09ec9e5eb3a
  category = json.loads(request.form.get('category')) 
  seed = np.array(json.loads(request.form.get('seed')))

  assert category >= 0
  assert category < 1000
  assert seed.shape == (1, 140)

  # Run the generator to produce images
  images = sample_with_category(sess, seed, category)

  # Format to image file
  array = np.asarray(imgrid(images, 1), dtype=np.uint8)
  imgBytes = imbytes(array)
  return send_file(imgBytes, attachment_filename='image.jpeg', mimetype='image/jpeg')

@app.route('/labels', methods=['POST'])
def generateFromLabels():
  global sess

  labels = np.array(json.loads(request.form.get('labels')))
  seed = np.array(json.loads(request.form.get('seed')))

  assert labels.shape == (1, 1000)
  assert seed.shape == (1, 140)

  # Run the generator to produce images
  images = sample_with_labels(sess, seed, labels)

  # Format to image file
  array = np.asarray(imgrid(images, 1), dtype=np.uint8)
  imgBytes = imbytes(array)
  return send_file(imgBytes, attachment_filename='image.jpeg', mimetype='image/jpeg')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081) 
