import cPickle
import maya.cmds as mc

def pyToAttr(objAttr, data):
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
    if not mc.objExists(objAttr):
        mc.addAttr(obj, longName=attr, dataType='string')
    # Make sure it is the correct type before modifing:
    if mc.getAttr(objAttr, type=True) != 'string':
        raise Exception("Object '%s' already has an attribute called '%s', but it isn't type 'string'"%(obj,attr))

    # Pickle the data and return the coresponding string value:
    stringData = cPickle.dumps(data)
    # Make sure attr is unlocked before edit:
    mc.setAttr(objAttr, edit=True, lock=False)
    # Set attr to string value:
    mc.setAttr(objAttr, stringData, type='string')
    # And lock it for safety:
    mc.setAttr(objAttr, edit=True, lock=True)

def attrToPy(objAttr):
    """
    Take previously stored (pickled) data on a Maya attribute (put there via
    pyToAttr() ) and read it back (unpickle) to valid Python values.

    Arguments:
    objAttr : string : A valid object.attribute name in the scene.  And of course,
        it must have already had valid Python data pickled to it.

    Return : some Python data :  The reconstituted, unpickled Python data.
    """
    # Get the string representation of the pickled data.  Maya attrs return
    # unicode vals, and cPickle wants string, so we convert:
    stringAttrData = str(mc.getAttr(objAttr))
    # Un-pickle the string data:
    loadedData = cPickle.loads(stringAttrData)

    return loadedData



# Define our node and attr name based on the selected object:
node = mc.ls(selection=True)[0]
objAttr = '%s.defaultAssignment'%node


specialData = {node:'some_mesh_identifier'}
print "Python data to store to Maya obj.attr:"
print specialData

# Store data to our node:
pyToAttr(objAttr, specialData)

# Later, get data back:
storedData = attrToPy(objAttr)
print "Restored Python Data:"
print storedData
