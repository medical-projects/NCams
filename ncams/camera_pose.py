#!python3
# -*- coding: utf-8 -*-
"""
NCams Toolbox
Copyright 2019 Charles M Greenspon, Anton Sobinov
https://github.com/CMGreenspon/NCams

Functions related to estimation of relative positions of the cameras.

For more details on the camera data structures and dicts, see help(ncams.camera_tools).
"""

import os
import easygui

import cv2
import numpy as np
import matplotlib
import matplotlib.pyplot as mpl_pp
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

from . import utils
from . import camera_io
from . import camera_tools


def charuco_board_detector(camera_config):
    '''Detects charuco board in all cameras.

    Should be run after cameras have been calibrated.

    Arguments:
        camera_config {dict} -- see help(ncams.camera_tools). Should have following keys:
            serials {list of numbers} -- list of camera serials.
            dicts {dict of 'camera_dict's} -- keys are serials, values are 'camera_dict'.
            pose_estimation_path {string} -- directory where pose estimation information is stored.

    Output:
        cam_image_points {list} -- matching points
        cam_charuco_ids {list} -- ids of points
    '''
    # Unpack the dict
    serials = camera_config['serials']
    names = [camera_config['dicts'][serial]['name'] for serial in serials]
    pose_estimation_path = camera_config['pose_estimation_path']

    # Get number of cameras
    num_cameras = len(serials)
    charuco_dict, charuco_board, _ = camera_tools.create_board(camera_config)

    # Get list of images for each camera
    cam_image_list = []
    num_images = np.zeros((1, num_cameras), dtype=int)
    for icam, name in enumerate(names):
        image_list = utils.get_image_list(path=os.path.join(pose_estimation_path, name))
        num_images[0, icam] = len(image_list)
        cam_image_list.append(image_list)

    # Crucial: Each camera must have the same number of images so that we can assume the order is
    # maintained and that they are synced
    if not np.ma.allequal(num_images, np.mean(num_images)):
        raise Exception('Image lists are of unequal size and may not be synced.')

    num_images = num_images[0, 0]
    cam_image_points = []
    cam_charuco_ids = []
    # Look at one synced image across cameras and find the matching points
    for image in range(num_images):
        im_ids, image_points = [], []  # reset for each image
        for icam, name in enumerate(names):
            # Load the image
            img = cv2.imread(os.path.join(pose_estimation_path, name,
                                          cam_image_list[icam][image]))
            # Detect the aruco markers and get IDs
            corners, ids, _ = cv2.aruco.detectMarkers(img, charuco_dict)
            if ids is not None:
                # Find the corners and IDs
                _, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
                    corners, ids, img, charuco_board)
                if isinstance(charuco_corners, np.ndarray):  # If present then append
                    image_points.append(charuco_corners)
                    im_ids.append(charuco_ids)
                else:  # For formatting/indexing
                    image_points.append([])
                    im_ids.append([])
            else:
                image_points.append([])
                im_ids.append([])
        # Concatenate them to get super list which can be parsed later
        cam_image_points.append(image_points)
        cam_charuco_ids.append(im_ids)

    return cam_image_points, cam_charuco_ids


def checkerboard_detector(camera_config):
    '''Get all image points and determine which calibration mode is better. ???
        AS: description seems wrong

    Should be run after cameras have been calibrated.

    Arguments:
        camera_config {dict} -- see help(ncams.camera_tools). Should have following keys:
            serials {list of numbers} -- list of camera serials.
            board_dim: list with the number of checks [height, width]
            dicts {dict of 'camera_dict's} -- keys are serials, values are 'camera_dict'.
            pose_estimation_path {string} -- directory where pose estimation information is stored.

    Output:
        cam_board_logit {list} -- if checkerboard: logical array (num_cameras, num_images)
            indicating in which images each camera detected a checkerboard.
        cam_image_points {list} -- if checkerboard: array of image points (num_cameras, image,
            (x, y))
        pose_strategy {string} -- string indicating which pose estimation strategy is ideal.
    '''
    # Unpack the dict
    serials = camera_config['serials']
    num_cameras = len(serials) # How many cameras are there
    names = [camera_config['dicts'][serial]['name'] for serial in serials]
    pose_estimation_path = camera_config['pose_estimation_path']
    board_dim = camera_config['board_dim']

    # Begin the checkerboard detection for each camera
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001) # Default criteria
    cam_board_logit = []
    cam_image_points = []

    print('Beginning checkerboard detection.')
    for icam, cam_name in enumerate(names):
        print('- Camera {} of {}.'.format(icam+1, num_cameras))
        cam_image_list = utils.get_image_list(path=os.path.join(pose_estimation_path, cam_name))

        # Analyze the images to get checkerboard corners
        image_points = []  # x,y image points
        board_logit = np.zeros((1, len(cam_image_list)), dtype=bool)

        for iimage, image_name in enumerate(cam_image_list):
            img = cv2.imread(image_name, 0) # Load as grayscale
            board_logit[0, iimage], corners = cv2.findChessboardCorners(
                img, (board_dim[0]-1, board_dim[1]-1), None)

            # If a checkerboard was found then append the image points variable for calibration
            if board_logit[0, iimage]:
                corners_refined = cv2.cornerSubPix(img, corners, (11, 11), (-1, -1), criteria)
                image_points.append(corners_refined)
            else:
                image_points.append([]) # To keep consistent with the board_logit list

        # Add exports to list structure
        cam_board_logit.append(board_logit)
        cam_image_points.append(image_points)

    print('* Checkerboard detection complete.')

    combined_board_logit = np.sum(np.vstack(cam_board_logit), 0) # Combine and sum the logits
    # See how many checkerboard detections are present across all cameras
    num_common_cb = np.sum(combined_board_logit == num_cameras)

    if num_common_cb < 10:
        pose_strategy = 'stereo_sequential'
    elif num_common_cb >= 10:
        pose_strategy = 'common'

    print('* Optimal pose strategy: "' + pose_strategy + '".')

    return cam_board_logit, cam_image_points, pose_strategy


def multi_camera_pose_estimation():
    '''[Short description]

    [Long description]

    Arguments:
        []
    Keyword Arguments:
        []
    Output:
        []
    '''
    raise NotImplementedError
    num_cameras = len(camera_config['camera_names'])
    if num_cameras == 1:
        raise Exception('Only one camera present, pose cannot be calculated with this function.')
        return []


def auto_pose_estimation(camera_config):
    '''[Short description]

    [Long description]

    Arguments:
        []
    Keyword Arguments:
        []
    Output:
        []
    '''
    raise NotImplementedError
    # Unpack the dict
    board_type = camera_config['board_type']
    num_cameras = len(camera_config['camera_names'])

    if board_type == 'charuco':
        # Create the board
        _, charuco_board, _ = create_board(camera_config)
        board_dims = charuco_board.getChessboardSize()
        num_corners = (board_dims[0]-1) * (board_dims[1]-1) # Need to know how to format the logit table
        # Get the ids and image points across images and cameras
        cam_image_points, cam_charuco_ids = charuco_board_detector(camera_config)
        # Parse the total number of shared points across all cameras
        pose_method = get_optimal_pose_method(cam_charuco_ids, board_type, num_corners)
        # Get all the poses
        if pose_method == 'common':
            world_locations, world_orientations = common_pose_estimation(camera_config,
                                                                         calibration_config,
                                                                         cam_image_points,
                                                                         cam_charuco_ids)
        else:
          return[]


    #if pose_strategy == 'stereo_sequential':
    export_pose_estimation(os.path.join(camera_config['folder_path'], 'pose_estimation'),
                           camera_config['camera_names'], world_locations, world_orientations)

    return world_locations, world_orientations


def get_optimal_pose_method(input_array, board_type, num_corners):
    '''[Short description]

    [Long description]

    Arguments:
        []
    Keyword Arguments:
        []
    Output:
        []
    '''
    raise NotImplementedError
    if board_type == 'charuco':
        num_images = len(input_array)
        num_cameras = len(input_array[0])
        shared_points_counter = np.zeros((len(input_array),1), dtype = int)
        for image in range(num_images):
            # Empty array with a spot for each corner and ID
            point_logit = np.zeros((num_corners, num_cameras), dtype = bool)
            for cam in range(num_cameras):
                # Get the array specific to the camera and image
                temp = input_array[image][cam]
                if isinstance(temp, np.ndarray):
                    for corner in temp:
                      point_logit[int(corner),cam] = True

    sum_point_logit = np.sum(point_logit.astype(int), 1)
    common_points = sum_point_logit == num_cameras
    shared_points_counter[image,0] = np.sum(common_points.astype(int))
    num_common_points = np.sum(shared_points_counter)

    if num_common_points >= 250:
      optimal_method = 'common'
    else:
      optimal_method = 'sequential-stereo'

    return optimal_method


def get_world_pose(camera_config):
    '''[Short description]

    [Long description]

    Arguments:
        []
    Keyword Arguments:
        []
    Output:
        []
    '''
    raise NotImplementedError


def one_shot_multi_PnP(camera_config, calibration_config):
    '''Position estimation based on a single frame from each camera.

    [Long description]

    Arguments:
        camera_config {dict} -- see help(ncams.camera_tools). Should have following keys:
            serials {list of numbers} -- list of camera serials.
            image_size {(height, width)} -- size of the images captured by the cameras.
            board_dim: list with the number of checks [height, width]
            dicts {dict of 'camera_dict's} -- keys are serials, values are 'camera_dict'.
            pose_estimation_path {string} -- directory where pose estimation information is stored.
        calibration_config {dict} -- see help(ncams.camera_tools). Should have following keys:
            distortion_coefficientss {list of np.arrays} -- distortion coefficients for each camera
            camera_matrices {list of np.arrays} -- the essential camera matrix for each camera.
            dicts {dict of 'camera_calib_dict's} -- keys are serials, values are
                'camera_calib_dict', see below.
    Output:
        pose_estimation_config {dict} -- information on estimation of relative position of all
                cameras and the results of said pose estimation. For more info, see
                help(ncams.camera_tools). Should have following keys:
            serials {list of numbers} -- list of camera serials.
            world_locations {list of np.arrays} -- world locations of each camera.
            world_orientations {list of np.arrays} -- world orientation of each camera.
            path {string} -- directory where pose estimation information is stored. Should be same
                as information in camera_config.
            filename {string} -- name of the YAML file to store the config in/load from.
            dicts {dict of 'camera_pe_dict's} -- keys are serials, values are 'camera_pe_dict',
                see below.

        camera_pe_dict {dict} -- info on pose estimation of a single camera. Sould have following
                keys:
            serial {number} -- UID of the camera.
            world_location {np.array} -- world location of the camera.
            world_orientation {np.array} -- world orientation of the camera.
    '''
    names = [camera_config['dicts'][serial]['name'] for serial in camera_config['serials']]
    pose_estimation_path = camera_config['pose_estimation_path']
    camera_matrices = calibration_config['camera_matrices']
    distortion_coefficientss = calibration_config['distortion_coefficientss']
    pose_estimation_path = camera_config['pose_estimation_path']

    charuco_dict, charuco_board, _ = camera_tools.create_board(camera_config)
    world_points = camera_tools.create_world_points(camera_config)
    h, w = camera_config['image_size']
    im_list = utils.get_image_list(path=pose_estimation_path)

    world_locations = []
    world_orientations = []
    for icam, name in enumerate(names):
        # Find the correct image
        im_name = [i for i in im_list if name in i]
        # If more than one image contains the camera name ask user to select
        if len(im_name) > 1:
            cwd = os.getcwd
            print('--> Multiple images contain the camera name. Select the correct file for'
                  ' "{}".'.format(name))
            os.chdir(pose_estimation_path)
            im_path = easygui.fileopenbox(title='Image selector',
                                          msg='select the image for "{}".'.format(name))
            os.chdir(cwd)
        else:
            im_path = os.path.join(pose_estimation_path, im_name[0])

        world_image = cv2.imread(im_path)

        # Get the image points
        # Detect the aruco markers and IDs
        corners, ids, _ = cv2.aruco.detectMarkers(world_image, charuco_dict)
        _, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
            corners, ids, world_image, charuco_board)
        # Get the optimal camera matrix
        temp_optim, _ = cv2.getOptimalNewCameraMatrix(camera_matrices[icam],
                                                      distortion_coefficientss[icam],
                                                      (w, h), 1, (w, h))
        # Undistort image points
        undistorted_points = cv2.undistortPoints(
            np.vstack(charuco_corners), camera_matrices[icam], distortion_coefficientss[icam],
            P=temp_optim)
        # Match to world points
        filtered_world_points = []
        for cid in charuco_ids:
            filtered_world_points.append(world_points[cid, :, :])
        filtered_world_points = np.vstack(filtered_world_points)

        # PnP
        _, rvec, tvec = cv2.solvePnP(
            filtered_world_points, undistorted_points,
            camera_matrices[icam], distortion_coefficientss[icam])
        # Append
        world_locations.append(tvec)
        world_orientations.append(rvec)

    # Make the output structure
    dicts = {}
    for icam, serial in enumerate(camera_config['serials']):
        dicts[serial] = {
            'serial': serial,
            'world_location': world_locations[icam],
            'world_orientation': world_orientations[icam]
        }

    pose_estimation_config = {
        'serials': camera_config['serials'],
        'world_locations': world_locations,
        'world_orientations': world_orientations,
        'path': camera_config['pose_estimation_path'],
        'filename': camera_config['pose_estimation_filename'],
        'dicts': dicts
    }

    return pose_estimation_config


def common_pose_estimation(camera_config, calibration_config, cam_image_points, detection_logit):
    '''Position estimation based on frames from multiple cameras simultaneously.

    If there are sufficient shared world points across all cameras then camera pose can
    be estimated from all of them simultaneously. This allows for more points to be used
    than with the one_shot method.

    Arguments:
        camera_config {dict} -- see help(ncams.camera_tools). Should have following keys:
            serials {list of numbers} -- list of camera serials.
            reference_camera_serial {number} -- serial number of the reference camera.
            image_size {(height, width)} -- size of the images captured by the cameras.
            board_dim: list with the number of checks [height, width]
            dicts {dict of 'camera_dict's} -- keys are serials, values are 'camera_dict'.
        calibration_config {dict} -- see help(ncams.camera_tools). Should have following keys:
            distortion_coefficientss {list of np.arrays} -- distortion coefficients for each camera
            camera_matrices {list of np.arrays} -- the essential camera matrix for each camera.
            dicts {dict of 'camera_calib_dict's} -- keys are serials, values are
                'camera_calib_dict', see below.
        cam_image_points {[type]} -- [description]
        detection_logit {[type]} -- [description]
    Output:
        pose_estimation_config {dict} -- information on estimation of relative position of all
                cameras and the results of said pose estimation. For more info, see
                help(ncams.camera_tools). Should have following keys:
            serials {list of numbers} -- list of camera serials.
            world_locations {list of np.arrays} -- world locations of each camera.
            world_orientations {list of np.arrays} -- world orientation of each camera.
            path {string} -- directory where pose estimation information is stored. Should be same
                as information in camera_config.
            filename {string} -- name of the YAML file to store the config in/load from.
            dicts {dict of 'camera_pe_dict's} -- keys are serials, values are 'camera_pe_dict',
                see below.

        camera_pe_dict {dict} -- info on pose estimation of a single camera. Sould have following
                keys:
            serial {number} -- UID of the camera.
            world_location {np.array} -- world location of the camera.
            world_orientation {np.array} -- world orientation of the camera.
    '''
    num_cameras = len(camera_config['serials'])
    camera_matrices = calibration_config['camera_matrices']
    distortion_coefficientss = calibration_config['distortion_coefficientss']

    # Determine the reference camera
    ireference_cam = camera_config['serials'].index(camera_config['reference_camera_serial'])

    h, w = camera_config['image_size']

    cam_idx = np.arange(0, num_cameras)
    secondary_idx = cam_idx[cam_idx != ireference_cam] # Get the indices of the non-primary cameras
    # Get the world points
    world_points = camera_tools.create_world_points(camera_config)
    corner_idx = np.arange(0, len(world_points))

    if camera_config['board_type'] == 'charuco':
        # Get all the points shared across cameras
        filtered_object_points = []
        filtered_image_points = [[] for icam in range(num_cameras)]
        for cip, detl in zip(cam_image_points, detection_logit):
            # Empty array with a spot for each corner and ID
            point_logit = np.zeros((len(world_points), num_cameras), dtype=bool)
            for icam in range(num_cameras):
                temp = detl[icam]  # Get the array specific to the camera and im
                if isinstance(temp, np.ndarray):
                    for corner in temp:  # For each detected corner
                        point_logit[int(corner), icam] = True
            sum_point_logit = np.sum(point_logit.astype(int), 1)

            # Find which points are shared across all cameras
            common_points = sum_point_logit == num_cameras
            if np.sum(common_points) >= 6:
                # Append only those points
                filtered_object_points.append(world_points[common_points, :].astype('float32'))
                for icam in range(num_cameras):
                    temp_corners = np.zeros((np.sum(common_points), 2), dtype=float)
                    temp_ids = detl[icam]
                    temp_points = cip[icam]
                    running_idx = 0
                    for corner in corner_idx[common_points]:  # Only append
                        idx = int(np.where(temp_ids == corner)[0])
                        temp_corners[running_idx, :] = temp_points[idx, :, :]
                        running_idx += 1
                    filtered_image_points[icam].append(temp_corners.astype('float32'))

    elif camera_config['board_type'] == 'checkerboard':
        raise NotImplementedError

    # Get the optimal matrices and undistorted points
    optimal_matrices, undistorted_points = [], []
    for icam in range(num_cameras):
        temp_optim, _ = cv2.getOptimalNewCameraMatrix(
            camera_matrices[icam], distortion_coefficientss[icam], (w, h), 1, (w, h))
        optimal_matrices.append(temp_optim)
        undistorted_points.append(cv2.undistortPoints(
            np.vstack(filtered_image_points[icam]), camera_matrices[icam],
            distortion_coefficientss[icam], P=optimal_matrices[icam]))

    # Perform the initial stereo calibration
    secondary_cam = secondary_idx[0]
    stereo_calib_flags = 0
    stereo_calib_flags |= cv2.CALIB_FIX_INTRINSIC
    criteria = (cv2.TERM_CRITERIA_EPS, 30, 0.001)

    reprojection_error, _, _, _, _, R, T, _, _ = cv2.stereoCalibrate(
        filtered_object_points, filtered_image_points[ireference_cam],
        filtered_image_points[secondary_cam],
        camera_matrices[ireference_cam], distortion_coefficientss[ireference_cam],
        camera_matrices[secondary_cam], distortion_coefficientss[secondary_cam],
        (w, h), None, None, None, criteria, stereo_calib_flags)

    if reprojection_error > 1:
        print('Poor initial stereo-calibration. Subsequent pose estimates may be innacurate.')

    # Make projection matrices
    # This keeps the reference frame to that of the primary camera
    projection_matrix_primary = np.dot(
        camera_matrices[ireference_cam], np.hstack((np.identity(3), np.zeros((3, 1)))))

    # Make the secondary projection matrix from calculated rotation & translation matrix
    projection_matrix_secondary = np.dot(camera_matrices[secondary_cam], np.hstack((R, T)))

    # Triangulate those same points
    triangulated_points_norm = cv2.triangulatePoints(
        projection_matrix_primary, projection_matrix_secondary,
        undistorted_points[ireference_cam], undistorted_points[secondary_cam])
    # Normalize:
    triangulated_points = triangulated_points_norm[:3, :] / np.transpose(
        np.repeat(triangulated_points_norm[3, :], 3).reshape((-1, 3)))

    world_orientations = []
    world_locations = []
    # Get pose from the triangulated points for all cameras
    for icam in range(num_cameras):
        _, rvec, tvec = cv2.solvePnP(
            np.transpose(triangulated_points), np.vstack(filtered_image_points[icam]),
            camera_matrices[icam], distortion_coefficientss[icam])
        world_orientations.append(rvec)
        world_locations.append(tvec)

    # Make the output structure
    dicts = {}
    for icam, serial in enumerate(camera_config['serials']):
        dicts[serial] = {
            'serial': serial,
            'world_location': world_locations[icam],
            'world_orientation': world_orientations[icam]
        }

    pose_estimation_config = {
        'serials': camera_config['serials'],
        'world_locations': world_locations,
        'world_orientations': world_orientations,
        'path': camera_config['pose_estimation_path'],
        'filename': camera_config['pose_estimation_filename'],
        'dicts': dicts
    }

    return pose_estimation_config


def sequential_pose_estimation(cam_board_logit, cam_image_points, reference_camera,
                               camera_matrices, distortion_coefficients):
    '''If insufficient shared points then we can instead use the reference pair of cameras and
    iteratively calibrate all other cameras.

    [Long description]

    Arguments:
        []
    Keyword Arguments:
        []
    Output:
        pose_estimation_config {dict} -- information on estimation of relative position of all
                cameras and the results of said pose estimation. For more info, see
                help(ncams.camera_tools). Should have following keys:
            serials {list of numbers} -- list of camera serials.
            world_locations {list of np.arrays} -- world locations of each camera.
            world_orientations {list of np.arrays} -- world orientation of each camera.
            path {string} -- directory where pose estimation information is stored. Should be same
                as information in camera_config.
            filename {string} -- name of the YAML file to store the config in/load from.
            dicts {dict of 'camera_pe_dict's} -- keys are serials, values are 'camera_pe_dict',
                see below.

        camera_pe_dict {dict} -- info on pose estimation of a single camera. Sould have following
                keys:
            serial {number} -- UID of the camera.
            world_location {np.array} -- world location of the camera.
            world_orientation {np.array} -- world orientation of the camera.
    '''
    raise NotImplementedError


def inspect_pose_estimation():
    '''If insufficient shared points then we can instead use the reference pair of cameras and
    iteratively calibrate all other cameras.

    [Long description]

    Arguments:
        []
    Keyword Arguments:
        []
    Output:
        []
    '''
    raise NotImplementedError
    image_index = 10
    cam_indices = [0, 1]

    # Load the images
    im_list1 = utils.get_image_list(os.path.join(camera_config['folder_path'],
                                         'pose_estimation', cam_names[cam_indices[0]]))
    im1 = matplotlib.image.imread(os.path.join(camera_config['folder_path'], 'pose_estimation',
                                  cam_names[cam_indices[0]], im_list1[image_index]))

    im_list2 = utils.get_image_list(os.path.join(camera_config['folder_path'],
                                                     'pose_estimation', cam_names[cam_indices[1]]))
    im2 = matplotlib.image.imread(os.path.join(camera_config['folder_path'], 'pose_estimation',
                                               cam_names[cam_indices[1]], im_list2[image_index]))

    # Detect the markers
    corners1, ids1, _ = cv2.aruco.detectMarkers(im1, charuco_dict)
    corners2, ids2, _ = cv2.aruco.detectMarkers(im2, charuco_dict)
    # Get the chessboard
    _, charuco_corners1, charuco_ids1 = cv2.aruco.interpolateCornersCharuco(corners1, ids1, im1, charuco_board)
    _, charuco_corners2, charuco_ids2 = cv2.aruco.interpolateCornersCharuco(corners2, ids2, im2, charuco_board)

    # Just get overlapping ones
    shared_ids, shared_world_points = [], []
    for id in charuco_ids1:
        if any(charuco_ids2 == id):
            shared_ids.append(id)
            shared_world_points.append(world_points[id,0,:])
    shared_ids = np.vstack(shared_ids)
    shared_world_points = np.vstack(shared_world_points).reshape(len(shared_ids), 1, 3)

    shared_corners1, shared_corners2 = [], []
    for id in shared_ids:
        idx1, _ = np.where(charuco_ids1 == id)
        shared_corners1.append(charuco_corners1[idx1,0,:])
        idx2, _ = np.where(charuco_ids2 == id)
        shared_corners2.append(charuco_corners2[idx2,0,:])

    shared_corners1 = np.vstack(shared_corners1).reshape(len(shared_ids), 1, 2)
    shared_corners2 = np.vstack(shared_corners2).reshape(len(shared_ids), 1, 2)

    cam_image_points, cam_charuco_ids = charuco_board_detector(camera_config)
    R, T = WORKING_common_pose_estimation(camera_config, cam_image_points, cam_charuco_ids, camera_matrices, distortion_coefficients)

    projection_primary = np.matmul(camera_matrices[0],np.hstack((np.identity(3), np.zeros((3,1)))))
    projection_secondary = np.matmul(camera_matrices[1],np.hstack((R, T)))

    # Now lets try to triangulate these shared points
    new_cam_mat1, _ = cv2.getOptimalNewCameraMatrix(camera_matrices[cam_indices[0]], distortion_coefficients[cam_indices[0]], (w,h), 1, (w,h))
    undistorted_points1 = cv2.undistortPoints(np.vstack(shared_corners1), camera_matrices[cam_indices[0]], distortion_coefficients[cam_indices[0]], P = new_cam_mat1)

    new_cam_mat2, _ = cv2.getOptimalNewCameraMatrix(camera_matrices[cam_indices[1]], distortion_coefficients[cam_indices[1]], (w,h), 1, (w,h))
    undistorted_points2 = cv2.undistortPoints(np.vstack(shared_corners2), camera_matrices[cam_indices[1]], distortion_coefficients[cam_indices[1]], P = new_cam_mat2)

    # Triangulate the points
    triangulated_points_norm = cv2.triangulatePoints(projection_primary, projection_secondary, undistorted_points1, undistorted_points2)
    triangulated_points = triangulated_points_norm[:3,:]/np.transpose(np.repeat(triangulated_points_norm[3,:], 3).reshape((-1,3)))

    # Reproject the points to each camera and verify
    reprojected_corners1,_ = cv2.projectPoints(triangulated_points, np.identity(3), np.zeros((3,1)),
                                             new_cam_mat1, distortion_coefficients[cam_indices[0]])
    reprojected_corners2,_ = cv2.projectPoints(triangulated_points, R, T,
                                             new_cam_mat2, distortion_coefficients[cam_indices[1]])

    fig, axs = matplotlib.pyplot.subplots(1,2, squeeze=False)
    axs[0,0].imshow(im1)
    axs[0,1].imshow(im2)
    for corner in range(len(shared_corners1)):
        axs[0,0].scatter(shared_corners1[corner, 0, 0], shared_corners1[corner, 0, 1], facecolors='none', edgecolors='b')
        axs[0,0].scatter(shared_corners1[corner, 0, 0], reprojected_corners1[corner, 0, 1], facecolors='none', edgecolors='r')

        axs[0,1].scatter(shared_corners2[corner, 0, 0], shared_corners2[corner, 0, 1], facecolors='none', edgecolors='b')
        axs[0,1].scatter(shared_corners2[corner, 0, 0], reprojected_corners2[corner, 0, 1], facecolors='none', edgecolors='r')


def plot_poses(pose_estimation_config, scale_factor=1):
    '''Creates a plot showing the location and orientation of all cameras.

    Creates a plot showing the location and orientation of all cameras given based on translation
    and rotation vectors. If your cameras are very close together or far apart you can change the
    scaling factor as necessary.

    Arguments:
        pose_estimation_config {dict} -- see help(ncams.camera_tools). Should have following keys:
            serials {list of numbers} -- list of camera serials.
            world_locations {list of np.arrays} -- world locations of each camera.
            world_orientations {list of np.arrays} -- world orientation of each camera.
    '''
    world_locations = pose_estimation_config['world_locations']
    world_orientations = pose_estimation_config['world_orientations']
    serials = pose_estimation_config['serials']
    num_cameras = len(serials)

    # Only accepts list format so check if this is true only when a single camera is present
    if num_cameras == 1:  # AS: Not sure if needed anymore
        if isinstance(world_locations, np.ndarray):
            world_locations = [world_locations]
        if isinstance(world_orientations, np.ndarray):
            world_orientations = [world_orientations]

    # Create a figure with axes
    fig = mpl_pp.figure()
    ax = fig.gca(projection='3d')

    # Keep the verts for setting the axes later
    cam_verts = [[] for _ in range(num_cameras)]
    for icam in range(num_cameras):
        # Get the vertices to plot appropriate to the translation and rotation
        cam_verts[icam], cam_center = camera_tools.create_camera(
            scale_factor=scale_factor,
            rotation_vector=world_orientations[icam],
            translation_vector=world_locations[icam])

        # Plot it and change the color according to it's number
        ax.add_collection3d(Poly3DCollection(
            cam_verts[icam], facecolors='C'+str(icam), linewidths=1, edgecolors='k', alpha=1))

        # Give each camera a label
        ax.text(np.asscalar(cam_center[0]), np.asscalar(cam_center[1]), np.asscalar(cam_center[2]),
                'Cam ' + str(serials[icam]))

    # mpl is weird about maintaining aspect ratios so this has to be done
    ax_min = np.min(np.hstack(cam_verts))
    ax_max = np.max(np.hstack(cam_verts))

    # Set the axes and viewing angle
    ax.set_xlim([ax_max, ax_min]) # Note that this is reversed so that the cameras are looking towards us
    ax.set_ylim([ax_min, ax_max])
    ax.set_zlim([ax_min, ax_max])
    ax.view_init(elev=105, azim=-90)

    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_zlabel('z')


#################### Camera plotting helper functions
def create_camera(scale_factor=1, rotation_vector=None, translation_vector=None):
    '''Create a typical camera shape.

    [description]

    Keyword Arguments:
        scale_factor {number} -- [description] (default: {1})
        rotation_vector {[type]} -- [description] (default: {None})
        translation_vector {[type]} -- [description] (default: {None})
    Output:
        camera_vertices {np.array} -- [description]
        cam_center {np.array} -- [description]
    '''
    # Lines:
    # Back of camera body
    #  Front of camera body/back of lens
    # Back of camera body
    cam_points = np.array([
        [0, 0, 0],       [1, 0, 0],       [1, 1, 0],       [0, 1, 0],
        [0.2, 0.2, 0.5], [0.8, 0.2, 0.5], [0.8, 0.8, 0.5], [0.2, 0.8, 0.5],
        [0.2, 0.2, 1],   [0.8, 0.2, 1],   [0.8, 0.8, 1],   [0.2, 0.8, 1]])

    # Set the origin as the back of the lens
    centering_vector = [0.5, 0.5, 0.5]
    cam_points = cam_points - centering_vector

    # Scale the points
    cam_points = cam_points * scale_factor

    # Move the camera
    cam_points = move_camera(cam_points, rotation_vector, translation_vector)

    # Get the vertices & center
    camera_vertices = get_camera_vertices(cam_points)
    cam_center = np.mean(cam_points[4:8, :], 0)
    cam_center[1] = cam_center[1] + scale_factor

    return camera_vertices, cam_center


def move_camera(cam_points, rotation_vector=None, translation_vector=None):
    '''Applies the appropriate rotation and translation to the camera points.

    [description]

    Arguments:
        cam_points {[type]} -- [description]

    Keyword Arguments:
        rotation_vector {np.array} -- [description] (default: {None})
        translation_vector {np.array} -- [description] (default: {None})
    '''
    # Check rotation vector format
    if rotation_vector is None:
        rotation_vector = np.identity(3) # Assume it's not rotating
    elif rotation_vector.shape == (3, 1) or rotation_vector.shape == (1, 3):
        # Make matrix if necessary
        rotation_vector = cv2.Rodrigues(rotation_vector)[0] # Convert to matrix

    if translation_vector is None:
        translation_vector = np.zeros((3, 1)) # Assume there is no translation
    elif translation_vector.shape == (1, 3):
        translation_vector = np.transpose(translation_vector) # Format

    # Create the translation vector
    translation_vector = np.matmul(-np.transpose(rotation_vector), translation_vector)

    # Rotate and then translate
    cam_points = np.transpose(np.matmul(np.transpose(rotation_vector), np.transpose(cam_points)))
    cam_points = cam_points - np.transpose(translation_vector)

    return cam_points


def get_camera_vertices(cam_points):
    '''Manual mapping of the camera points from in create_camera.

    [description]

    Arguments:
        cam_points {list} -- 12-element array.
    Output:
        cam_verts {list 9x4} -- [description]
    '''
    cam_verts = [
        [cam_points[0], cam_points[4], cam_points[5], cam_points[1]],
        [cam_points[1], cam_points[5], cam_points[6], cam_points[2]],
        [cam_points[2], cam_points[6], cam_points[7], cam_points[3]],
        [cam_points[3], cam_points[7], cam_points[4], cam_points[0]], # Sides of lenses
        [cam_points[4], cam_points[8], cam_points[9], cam_points[5]],
        [cam_points[5], cam_points[9], cam_points[10], cam_points[6]],
        [cam_points[6], cam_points[10], cam_points[11], cam_points[7]],
        [cam_points[7], cam_points[11], cam_points[8], cam_points[4]],  # Sides of body
        [cam_points[8], cam_points[9], cam_points[10], cam_points[11]]]  # Back of body

    return cam_verts