# -*- coding: utf-8 -*-
"""Vertebrae Data Preprocessing.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1pX44MMg_YV71twc4ZjlB8OvpI58WBts4
"""

import os
import cv2 as cv
from math import atan2, cos, sin, sqrt, pi, ceil, floor
import numpy as np
from urllib.parse import urljoin
from google.colab.patches import cv2_imshow

# mount to drive
from google.colab import drive
drive.mount("/content/drive")

BASE_PATH = "/content/drive/MyDrive/vertebrates_data/"
TRAIN_PATH = urljoin(BASE_PATH, "train/")
TEST_PATH = urljoin(BASE_PATH, "test/")
PROC_TRAIN = urljoin(BASE_PATH, "processed/train/")
PROC_TEST = urljoin(BASE_PATH, "processed/test/")
GREEN = (0, 255, 0)

def get_contours(image):
  try:
    # Convert image to grayscale
    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
  except:
    print("image = image.astype('uint8')")
    image = image.astype('uint8')
    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

  # Convert image to binary
  _, bw = cv.threshold(gray, 10, 255, cv.THRESH_BINARY | cv.THRESH_OTSU)

  # Find all the contours in the thresholded image
  contours, _ = cv.findContours(bw, cv.RETR_LIST, cv.CHAIN_APPROX_NONE)

  return contours


def sorting(numbers_array):
  return sorted(numbers_array, key=abs)

def draw_axis(image, p_, q_, color, scale):
  p = list(p_)
  q = list(q_)

  ## [visualization1]
  angle = atan2(p[1] - q[1], p[0] - q[0]) # angle in radians
  hypotenuse = sqrt((p[1] - q[1]) * (p[1] - q[1]) + (p[0] - q[0]) * (p[0] - q[0]))

  # Here we lengthen the arrow by a factor of scale
  q[0] = p[0] - scale * hypotenuse * cos(angle)
  q[1] = p[1] - scale * hypotenuse * sin(angle)
  cv.line(image, (int(p[0]), int(p[1])), (int(q[0]), int(q[1])), color, 3, cv.LINE_AA)

  # create the arrow hooks
  p[0] = q[0] + 9 * cos(angle + pi / 4)
  p[1] = q[1] + 9 * sin(angle + pi / 4)
  cv.line(image, (int(p[0]), int(p[1])), (int(q[0]), int(q[1])), color, 3, cv.LINE_AA)

  p[0] = q[0] + 9 * cos(angle - pi / 4)
  p[1] = q[1] + 9 * sin(angle - pi / 4)
  cv.line(image, (int(p[0]), int(p[1])), (int(q[0]), int(q[1])), color, 3, cv.LINE_AA)
  ## [visualization1]


def draw_pca(image, mean, eigenvectors, eigenvalues):
  # Store the center of the object
  cntr = (int(mean[0,0]), int(mean[0,1]))
  ## [pca]

  ## [visualization]
  # Draw the principal components
  cv.circle(image, cntr, 3, (255, 0, 255), 2)
  p1 = (cntr[0] + 0.02 * eigenvectors[0,0] * eigenvalues[0,0], cntr[1] + 0.02 * eigenvectors[0,1] * eigenvalues[0,0])
  p2 = (cntr[0] - 0.02 * eigenvectors[1,0] * eigenvalues[1,0], cntr[1] - 0.02 * eigenvectors[1,1] * eigenvalues[1,0])
  draw_axis(image, cntr, p1, (255, 255, 0), 1)
  draw_axis(image, cntr, p2, (0, 0, 255), 5)


def get_orientation(pts, image):
  ## [pca]
  # Construct a buffer used by the pca analysis
  sz = len(pts)
  data_pts = np.empty((sz, 2), dtype=np.float64)
  for i in range(data_pts.shape[0]):
    data_pts[i,0] = pts[i,0,0]
    data_pts[i,1] = pts[i,0,1]

  # Perform PCA analysis
  mean = np.empty((0))
  mean, eigenvectors, eigenvalues = cv.PCACompute2(data_pts, mean)

  # draw PCA
  draw_pca(image, mean, eigenvectors, eigenvalues)

  # orientation in radians
  angle = atan2(eigenvectors[0,1], eigenvectors[0,0])
  return angle


def set_orientation(image):
  contours = get_contours(image)
  angles = []
  for i, c in enumerate(contours):
    # Calculate the area of each contour
    area = cv.contourArea(c)
    # Ignore contours that are too small or too large
    if area < 3700 or 100000 < area:
      continue

    # Find the orientation of each shape
    rad_ang = get_orientation(c, image)
    angles.append(int(np.rad2deg(rad_ang)))

  print(' Angles = {}'.format(angles))
  #---
  # Draw each contour only for visualisation purposes
  # cv.drawContours(image, contours, -1, GREEN, 2)
  # cv2_imshow(image)
  #---

  if angles:
    angles = sorting(angles)
    angle = angles[0]

    # TODO skip rotation for asimetric images
    if abs(angle) < 10:
      image_center = tuple(np.array(image.shape[1::-1]) / 2)
      rot_mat = cv.getRotationMatrix2D(image_center, angle, 1.0)
      image = cv.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv.INTER_LINEAR)
    else:
      cv2_imshow(image)

  return image

def brighter(image):
  gamma = 0.4
  lookUpTable = np.empty((1,256), np.uint8)
  for i in range(256):
      lookUpTable[0,i] = np.clip(pow(i / 255.0, gamma) * 255.0, 0, 255)

  image = cv.LUT(image, lookUpTable)
  return image

def histogram_equal(image):
  gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
  # create a CLAHE object
  clahe = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
  image = clahe.apply(gray)

  return image

def set_center(image):
  contours = get_contours(image)

  height, width, _ = image.shape
  min_x, min_y = width, height
  max_x = max_y = 0

  # computes the bounding box for the contour, and draws it on the image
  for contour in contours:
      (x,y,w,h) = cv.boundingRect(contour)
      min_x, max_x = min(x, min_x), max(x+w, max_x)
      min_y, max_y = min(y, min_y), max(y+h, max_y)

  #--- draw the box
  # if max_x - min_x > 0 and max_y - min_y > 0:
  #     cv.rectangle(image, (min_x, min_y), (max_x, max_y), GREEN, 2)
  #     cv2_imshow(image)
  #---


  # make it square (h and w to have the same value)
  # for delta_dist choose the minimum between: [delta between h and w,
  #                       min_x distance from frame, max_x distance from frame]

  if w > h:
    delta_dist = min(floor((w - h) / 2), height - max_y, min_y)

    from_y = min_y - delta_dist
    to_y = max_y + delta_dist
    from_x = min_x
    to_x = max_x
  else:
    delta_dist = min(floor((h - w) / 2), width - max_x, min_x)
    from_y = min_y
    to_y = max_y
    from_x = min_x - delta_dist
    to_x = max_x + delta_dist

  # cropped the image: image[y:y+h, x:x+w]
  # cropped_image = image[min_y:max_y, min_x:max_x]
  cropped_image = image[from_y:to_y, from_x:to_x]

  return cropped_image

def resize_img(image):
  new_size = (240, 240)
  return cv.resize(image, new_size, interpolation = cv.INTER_LINEAR)

def preprocess_image(path, output_path):
  image = cv.imread(path)
  assert image is not None, "file could not be read, check with os.path.exists()"

  # brightness
  image = brighter(image)

  # CLAHE
  image = histogram_equal(image)
  #       TODO improve:
  cv.imwrite("/content/drive/MyDrive/vertebrates_data/CLAHE.jpg", image)
  image = cv.imread("/content/drive/MyDrive/vertebrates_data/CLAHE.jpg")

  # set orientation
  image = set_orientation(image)

  # set image to the center
  image = set_center(image)

  # resize the image
  image = resize_img(image)

  # save
  cv.imwrite(output_path, image)

# main:

class_names = ['L1 SUPERIOR/', 'L2 SUPERIOR/', 'L3 SUPERIOR/', 'L4 SUPERIOR/', 'L5 SUPERIOR/']
for i, c in enumerate(class_names):
  path = urljoin(TEST_PATH, c)
  # path = urljoin(TRAIN_PATH, c)

  fnames = os.listdir(path)

  for filename in fnames:
    # /content/drive/MyDrive/vertebrates_data/test/L1 SUPERIOR/MARC_HTH-1130 ADULT MALE BLACK L1.jpg
    path = urljoin(TEST_PATH, urljoin(c, filename))
    # path = urljoin(TRAIN_PATH, urljoin(c, filename))

    # /content/drive/MyDrive/vertebrates_data/processed/test/L1 SUPERIOR/MARC_HTH-1130 ADULT MALE BLACK L1.jpg
    jpg_filename = "{}.jpg".format(filename.split('.')[0])
    output_path = urljoin(PROC_TEST, urljoin(c, jpg_filename))
    # output_path = urljoin(PROC_TRAIN, urljoin(c, jpg_filename))

    print(path)
    print(output_path)

    # preprocess_image(path, output_path)
    cv.waitKey(0)
    cv.destroyAllWindows()