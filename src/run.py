#technical packages
import json

#work packages
import math

import numpy as np

import cv2

import skimage.io
from skimage import exposure, morphology, measure
from skimage.transform import (hough_line, hough_line_peaks)

"""main code"""
def main(*images):

    output=[]

    def classifyLines(vLines, tolerance_verticale = 30):

        lines = []
        for line in vLines:
            (x0, y0, x1, y1) = line
            diff_x = abs(x1 - x0)
            if diff_x <= tolerance_verticale: 
                lines.append((x0, y0, x1, y1))
            else:  
                continue
        
        return lines

    def intersectLines(pt1, pt2, ptA, ptB):

        DET_TOLERANCE = 0.00000001

        x1, y1 = pt1;   x2, y2 = pt2
        dx1 = x2 - x1;  dy1 = y2 - y1
        x, y = ptA;   xB, yB = ptB;
        dx = xB - x;  dy = yB - y;

        DET = (-dx1 * dy + dy1 * dx)

        if math.fabs(DET) < DET_TOLERANCE: return (0,0,0,0,0)
        DETinv = 1.0/DET
        r = DETinv * (-dy  * (x-x1) +  dx * (y-y1))
        s = DETinv * (-dy1 * (x-x1) + dx1 * (y-y1))
        xi = (x1 + r*dx1 + x + s*dx)/2.0
        yi = (y1 + r*dy1 + y + s*dy)/2.0
        valid = 0
        
        if x1 != x2:
            if x1 < x2:
                a = x1
                b = x2
            else:
                a = x2
                b = x1
            c = xi
        else:
            if y1 < y2:
                a = y1
                b = y2
            else:
                a = y2
                b = y1
            c = yi
        if (c > a) and (c < b):
            if x != xB:
                if x < xB:
                    a = x
                    b = xB
                else:
                    a = xB
                    b = x
                c = xi
            else:
                if y < yB:
                    a = y
                    b = yB
                else:
                    a = yB
                    b = y
                c = yi
            if (c > a) and (c < b):
                valid = 1

        return (xi,yi,valid,r,s)
    
    def calculateAngles(pt1, pt2, ptA, ptB):
    
        dx1 = pt2[0] - pt1[0]
        dy1 = pt2[1] - pt1[1]
        dx2 = ptB[0] - ptA[0]
        dy2 = ptB[1] - ptA[1]
    
        if dy1 == 0:
            alpha1 = 90.0
        elif dx1 == 0:
            alpha1 = 0.0
        else:
            alpha1 = np.degrees(np.arctan(dy1 / dx1))
    
        if dy2 == 0:
            alpha2 = 90.0
        elif dx2 == 0:
            alpha2 = 0.0
        else:
            alpha2 = np.degrees(np.arctan(dy2 / dx2))
    
        angle = abs(alpha1 - alpha2)

        return angle

    thetas = np.arange(-np.pi / 4, np.pi / 4, np.pi / 64).astype(float)

    for image in images:

        """FIRST PART: GET THE IMAGE READY FOR THE EVALUATION"""
        # image acquisition
        imagebw = skimage.io.imread(image, as_gray=True)

        # image enhancement
        img_enhanced = exposure.equalize_adapthist(imagebw)
        img_filtered = cv2.medianBlur(img_enhanced.astype('float32'), 3)
    
        # image segmentation
        block_size = 19
        threshold = skimage.filters.threshold_otsu(img_filtered,block_size)
        img_seg = img_filtered < threshold

        # morphological operations
        img_op = morphology.binary_opening(img_seg)
        img_morpho = morphology.area_closing(img_op)

        # object description
        label = measure.label(img_morpho, background=0)
        props = measure.regionprops_table(label, image, properties=['label','area','equivalent_diameter','mean_intensity','solidity'])
        maxval = max(props['area'])
        img_labelled = morphology.remove_small_objects(label, min_size=maxval-1)

        # skeletonisation
        img_skeleton = morphology.skeletonize(img_labelled)

        """SECOND PART: PREPARATION TO EVALUATION"""
        # get the horizontal line
        vertical = []
        #lines = []
        intersections = []
        angles = []

        xx,yy = np.nonzero(img_skeleton)
        indmin = np.argmin(yy)
        indmax = np.argmax(yy)
        incision_line = ((yy[indmin],xx[indmin],yy[indmax],xx[indmax]))

        # get the vertical ones
        h, theta, d = hough_line(img_skeleton, theta=thetas)

        for _, angle, dist in zip(*hough_line_peaks(h, theta, d)):
            im_copie = img_skeleton.copy()
            im_copie[0:,:int(dist)-10] = 0
            im_copie[0:,int(dist)+10:] = 0
            yyy, xxx = np.nonzero(im_copie)

            if yyy.size == 0 or xxx.size ==0:
                continue
            else:
                indmin = np.argmin(yyy)  
                indmax = np.argmax(yyy)
                
                x0 = (dist - yyy[indmin]*np.sin(angle)) / np.cos(angle)
                x1 = (dist - yyy[indmax]*np.sin(angle)) / np.cos(angle)

                cord = ((x0, yyy[indmin], x1, yyy[indmax]))

            if not np.isnan(x0) and not np.isnan(x1) and not np.isnan(yyy[indmin]) and not np.isnan(yyy[indmax]):
                if cord not in vertical:
                    vertical.append(cord)

        # lightly clean the lines obtained to avoid detection errors
        lines = classifyLines(vertical)

        # get the coordinates and the angles of intersections between the main incision and the vertical lines
        for line in range(len(lines)):
            intersections.append(intersectLines(incision_line[:2], incision_line[2:], lines[line][:2], lines[line][2:])[:2])
            angles.append(calculateAngles(incision_line[:2], incision_line[2:], lines[line][:2], lines[line][2:]))

        """JSON OUTPUT"""
        data = [
            { "filename": "ok",
              "incision_polyline": incision_line,
              "crossing_positions": intersections,
              "crossing_angles": angles,
            }, 
        ]

        output.append(data)

    return(output)