from maya import cmds
import pymel.core as pm
import os


def stringAttr(objAttr, data):
    """
    Write (pickle) Python data to the given Maya obj.attr.  This data can
    later be read back (unpickled) via attrToPy().

    Arguments:
    objAttr : string : a valid object.attribute name in the scene.  If the
        object exists, but the attribute doesn't, the attribute will be added.
        The if the attribute already exists, it must be of type 'string', so
        the Python data can be written to it.
    data : some Python data :  Data that will be pickled to the attribute
        in question.
    """
    obj, attr = objAttr.split('.')
    # Add the attr if it doesn't exist:
    if not cmds.objExists(objAttr):
        cmds.addAttr(obj, longName=attr, dataType='string')
    # Make sure it is the correct type before modifing:
    if cmds.getAttr(objAttr, type=True) != 'string':
        raise Exception("Object '%s' already has an attribute called '%s', but it isn't type 'string'"%(obj,attr))

    # Pickle the data and return the coresponding string value:
    #stringData = json.dumps(data)
    # Make sure attr is unlocked before edit:
    cmds.setAttr(objAttr, edit=True, lock=False)
    # Set attr to string value:
    cmdscmds.setAttr(objAttr, data, type='string')
    # And lock it for safety:
    cmds.setAttr(objAttr, edit=True, lock=True)


def assetID(create=True):

    if create:
        sel = cmds.ls(sl=True)

        asset = os.getenv('ASSET_BUILD')

        for s in sel:
            stringAttr('{}.assetid'.format(s), '{}/{}'.format(asset, s))

            shape = cmds.listRelatives(s, shapes=True)
            if shape:
                shape = str(shape[0])
                stringAttr('{}.assetid'.format(shape), '{}/{}'.format(asset, s))
    else:

        asset = os.getenv('ASSET_BUILD')

        for s in sel:
            attr = '{}.assetid'.format(s)
            cmds.setAttr(attr, edit=True, lock=False)
            cmds.deleteAttr(attr)

            shape = cmds.listRelatives(s, shapes=True)
            if shape:
                shape = str(shape[0])
                attr = '{}.assetid'.format(shape)
                cmds.setAttr(attr, edit=True, lock=False)
                cmds.deleteAttr(attr)

def camrig():
    import rigLib.base as rb

    sel = pm.ls(sl=True)

    if len(sel) == 0:
        sel = pm.camera(n='shot_cam')[0]
        pm.rename(sel, 'shot_cam')

    units = cmds.currentUnit(q=1, linear=1)
    print units

    scaleCtl = 1
    if units == 'm':
        scaleCtl = 0.1
    elif scaleCtl == 'cm':
        scaleCtl = 1

    for node in sel:

        camShape = node.getShape()
        camShape.locatorScale.set(10)
        camShape.displayGateMaskColor.set([0.03, 0.03, 0.03])
        camShape.overscan.set(1.1)

        mainCtlObj = rb.control.Control(prefix='cam', translateTo=node.name(), rotateTo=node.name(), shape='circleZ', scale=scaleCtl)
        shakeCtlObj = rb.control.Control(prefix='shake', translateTo=node.name(), rotateTo=node.name(), shape='circleZ', scale=scaleCtl*0.6, lockChannels=['s', 'v', 'r'])

        mainCtl = pm.PyNode(mainCtlObj.C)
        mainOffset = pm.PyNode(mainCtlObj.Off)
        shakeCtl = pm.PyNode(shakeCtlObj.C)
        shakeOffset = pm.PyNode(shakeCtlObj.Off)

        shakeCtl.addAttr('speed', keyable=True, attributeType='float', min=0.0)
        shakeCtl.addAttr('amplitude', keyable=True, attributeType='float', min=0.0)

        expressionString = '\
            $speed = {0}.speed;\
            $amp = {0}.amplitude;\
            {0}.tx = noise((frame*0.4)*$speed)*$amp;\
            {0}.ty = noise((frame*0.6)*$speed)*$amp;\
            '.format(shakeCtl.name())

        pm.expression( s=expressionString, n='camShake_exp' )

        pm.parent(node, shakeCtl)
        pm.parent(shakeOffset, mainCtl)

def switch_format(aspect=1.78):

    resolution = pm.PyNode('defaultResolution')

    height = resolution.width.get() / aspect

    resolution.height.set(height)


def fit_object():

    import pymel.core as pm
    # Position the active camera to view the active objects
    pm.viewFit()

    # Position cameraShape-1 to view all objects
    pm.viewFit( 'cameraShape1', all=True )

    # Fill 50 percent of the active view with active objects
    pm.viewFit( f=0.9 )

    pm.viewFit( all=True )

fit_object()
