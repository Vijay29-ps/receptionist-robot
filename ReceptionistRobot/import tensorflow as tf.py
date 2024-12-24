import tensorflow as tf

# Path to the saved model
model_path = "/home/vps/tensorflow_model/saved_model/ssd_mobilenet_v2_coco_2018_03_29/saved_model"

# Load the model
model = tf.saved_model.load(model_path)

# Print the model signatures to verify successful loading
print(model.signatures)
