import numpy as np
import cv2
import glob
import time
import argparse
import os
import sys

parser = argparse.ArgumentParser(description='Calibrates cameras using chessboard calibration')
parser.add_argument('--path', help='Path to preexisting training files', required=False)
parser.add_argument('--num', help='Number of images to calibrate using, default is 10', required=False)

imagesl = None
imagesr = None
args = parser.parse_args()

if args.path:
    if not os.path.isdir(args.path) or len(os.listdir(args.path)) == 0:
        print('Invalid or empty directory')
        sys.exit()
    else:
        imagesl = glob.glob('{}*l.jpg'.format(args.path))
        imagesr = glob.glob('{}*r.jpg'.format(args.path))


# termination criteria
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
objp = np.zeros((9*6,3), np.float32)
objp[:,:2] = np.mgrid[0:9,0:6].T.reshape(-1,2)

# Arrays to store object points and image points from all the images.
objpoints = [] # 3d point in real world space
imgpointsl = [] # 2d points in image plane on left camera
imgpointsr = [] # 2d points in image plane on right camera


# Gathering data
num = -1

if args.num:
    num = args.num
else:
    num = 10

num_pics = 0

shapel = None
shaper = None

if imagesl == None or imagesr == None:
    videol = cv2.VideoCapture(0)
    videor = cv2.VideoCapture(1)

    #videol.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    videor.set(cv2.CAP_PROP_AUTOFOCUS, 0)

    while num_pics < num:
        ret, framel = videol.read()
        ret, framer = videor.read()
        grayl = cv2.cvtColor(framel, cv2.COLOR_BGR2GRAY)
        grayr = cv2.cvtColor(framer, cv2.COLOR_BGR2GRAY)

        #cv2.imshow('framel', framel)
        #cv2.imshow('framer', framer)

        #cv2.waitKey(1000)

        print('looking for corners')
        foundl, cornersl = cv2.findChessboardCorners(grayl, (9,6), None)
        foundr, cornersr = cv2.findChessboardCorners(grayr, (9,6), None)
        if foundl == foundr == True:
            cv2.imwrite('./images/chessboard-{}l.jpg'.format(num_pics), grayl)
            cv2.imwrite('./images/chessboard-{}r.jpg'.format(num_pics), grayr)
            num_pics += 1

            objpoints.append(objp)
            imgpointsl.append(cornersl)
            imgpointsr.append(cornersr)

            print('Found chessboard, waiting 5 seconds')
            start = time.time()
            now = start

            while now - start < 5:
                # avoid the video advancing when we don't want it to

                framel = videol.read()
                framer = videor.read()
                #cv2.imshow('left', framel)
                #cv2.imshow('right', framer)

                #cv2.waitKey(1)
                now = time.time()

        #cv2.waitKey(1)
    
    videol.release()
    videor.release()
    cv2.destroyAllWindows()
else:
    # We already have an image directory

    for imagel, imager in zip(imagesl, imagesr):
        imgl = cv2.imread(imagel)
        grayl = cv2.cvtColor(imgl, cv2.COLOR_BGR2GRAY)

        imgr = cv2.imread(imager)
        grayr = cv2.cvtColor(imgr, cv2.COLOR_BGR2GRAY)

        foundl, cornersl = cv2.findChessboardCorners(grayl, (9,6), None)
        foundr, cornersr = cv2.findChessboardCorners(grayr, (9,6), None)

        if foundl == foundr == True:
            objpoints.append(objp)
            imgpointsl.append(cornersl)
            imgpointsr.append(cornersr)

# Actual calibration
retl, mtxl, distl, rvecsl, tvecsl = cv2.calibrateCamera(objpoints, imgpointsl, grayl.shape[::-1], None, None)
retr, mtxr, distr, rvecsr, tvecsr = cv2.calibrateCamera(objpoints, imgpointsr, grayr.shape[::-1], None, None)

imgl = cv2.imread('./images/chessboard-5l.jpg')
h, w = imgl.shape[:2]
newcameramtxl, roil = cv2.getOptimalNewCameraMatrix(mtxl, distl, (w,h), 1, (w,h))

undistorted = cv2.undistort(imgl, mtxl, distl, None, newcameramtxl)
x, y, w, h = roil
undistorted = undistorted[y:y+h, x:x+w]
cv2.imwrite('./generated/resultl.jpg', undistorted)

imgr = cv2.imread('./images/chessboard-5r.jpg')
h, w = imgr.shape[:2]
newcameramtxr, roir = cv2.getOptimalNewCameraMatrix(mtxr, distr, (w,h), 1, (w,h))

undistorted = cv2.undistort(imgr, mtxr, distr, None, newcameramtxr)
x, y, w, h = roir
undistorted = undistorted[y:y+h, x:x+w]
cv2.imwrite('./generated/resultr.jpg', undistorted)

mean_error = 0
for i in range(len(objpoints)):
    imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecsl[i], tvecsl[i], mtxl, distl)
    error = cv2.norm(imgpointsl[i], imgpoints2, cv2.NORM_L2)/len(imgpoints2)
    mean_error += error
print( "total error(left): {}".format(mean_error/len(objpoints)) )

mean_error = 0
for i in range(len(objpoints)):
    imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecsr[i], tvecsr[i], mtxr, distr)
    error = cv2.norm(imgpointsr[i], imgpoints2, cv2.NORM_L2)/len(imgpoints2)
    mean_error += error
print( "total error(right): {}".format(mean_error/len(objpoints)) ) 

# Stereo stuff
error, mtxl, distl, mtxr, distr, R, T, E, F = cv2.stereoCalibrate(objpoints, imgpointsl, imgpointsr, mtxl, distl, mtxr, distr, grayl.shape[:2], None, None, None, None, flags=cv2.CALIB_FIX_INTRINSIC + cv2.CALIB_RATIONAL_MODEL + cv2.CALIB_FIX_PRINCIPAL_POINT)

rectifl, rectifr, projl, projr, disparityToDepthMap, roil, roir = cv2.stereoRectify(mtxl, distl, mtxr, distr, grayl.shape[:2], R, T, None, None, None, None, None, cv2.CALIB_ZERO_DISPARITY)

mapXl, mapYl = cv2.initUndistortRectifyMap(mtxl, distl, rectifl, projl, grayl.shape[:2], cv2.CV_32FC1)

mapXr, mapYr = cv2.initUndistortRectifyMap(mtxr, distr, rectifr, projr, grayr.shape[:2], cv2.CV_32FC1)

framel = cv2.imread('./images/chessboard-10l.jpg')
framer = cv2.imread('./images/chessboard-10r.jpg')

undistorted_rectifiedl = cv2.remap(framel, mapXl, mapYl, cv2.INTER_LINEAR)
undistorted_rectifiedr = cv2.remap(framer, mapXr, mapYr, cv2.INTER_LINEAR)

cv2.imshow('rectifiedl', undistorted_rectifiedl)
cv2.imshow('rectifiedr', undistorted_rectifiedr)

cv2.waitKey(0)

np.savez_compressed('./generated/calibration', imageSize=grayl.shape[:2], leftMapX=mapXl, leftMapY=mapYl, leftROI=roil, rightMapX=mapXr, rightMapY=mapYr, rightROI=roir)

print('stereo calibraiton error: {}'.format(error))