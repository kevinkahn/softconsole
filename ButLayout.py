import config


def InBut(pos,center,size):
    if (pos[0] > center[0] - size[0]/2) and (pos[0] < center[0] + size[0]/2) and (pos[1] > center[1] - size[1]/2) and (pos[1] < center[1] + size[1]/2):
        return True
    else:
        return False
        
