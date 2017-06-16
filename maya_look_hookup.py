# Code courtesy of shotgun software
import maya.cmds as cmds
import json_to_attr as jta
import pymel.core as pm
import json
import re
import pprint


def export_shader(nodes, output_file):

    shading_groups = set()
    shaders = set()

    for node in nodes:
        print "Processed mesh:" + node
        if cmds.ls(node, dag=True, type="mesh"):
            faces = cmds.polyListComponentConversion(node, toFace=True)
            for shading_group in cmds.listSets(type=1, object=faces[0]):
                print shading_group
                shading_groups.add(shading_group)

                connections = cmds.listConnections(
                    shading_group, source=True, destination=False)

                for shader in cmds.ls(connections, materials=True):
                    print 'Shader: ' + shader
                    shaders.add(shader)

                    shaderAttr = '{}.defaultAssignment'.format(shader)

                    pynode = pm.PyNode(node)
                    transformNode = pm.listRelatives(pynode, type='transform',p=True)[0]
                    assignData = {
                        'nameid': transformNode.nameid.get(),
                        }

                    print "Python data to store to Maya shader.attr:"
                    print assignData

                    # Store data to our node:
                    jta.pyToAttr(shaderAttr, assignData)

    select_nodes = list(shaders)

    cmds.select(select_nodes, replace=True)

    # write a .ma file to the publish path with the shader network definitions
    cmds.file(
        output_file,
        type='mayaAscii',
        exportSelected=True,
        options="v=0",
        prompt=False,
        force=True
        )

def store_shader():
    shading_groups = set()
    shaders = set()

    for node in nodes:
        print "Processed mesh:" + node
        if cmds.ls(node, dag=True, type="mesh"):
            faces = cmds.polyListComponentConversion(node, toFace=True)
            for shading_group in cmds.listSets(type=1, object=faces[0]):
                print shading_group
                shading_groups.add(shading_group)

                connections = cmds.listConnections(
                    shading_group, source=True, destination=False)

                for shader in cmds.ls(connections, materials=True):
                    print 'Shader: ' + shader
                    shaders.add(shader)

                    shaderAttr = '{}.defaultAssignment'.format(shader)

                    pynode = pm.PyNode(node)
                    transformNode = pm.listRelatives(pynode, type='transform',p=True)[0]
                    assignData = {
                        'nameid': transformNode.nameid.get(),
                        }

                    print "Python data to store to Maya shader.attr:"
                    print assignData

                    # Store data to our node:
                    jta.pyToAttr(shaderAttr, assignData)

    select_nodes = list(shaders)

    cmds.select(select_nodes, replace=True)

    # write a .ma file to the publish path with the shader network definitions
    cmds.file(
        output_file,
        type='mayaAscii',
        exportSelected=True,
        options="v=0",
        prompt=False,
        force=True
        )


def hookup_shaders(meshes=None, shaders=None):

    # hookup_prefix = "SHADER_HOOKUP_"
    shader_hookups = {}

    if not shaders:
        shaders = pm.ls(materials=True)

    # get all shaders
    for shader in shaders:
        #filter out shaders with defaultAssignment
        if not shader.hasAttr('defaultAssignment'):
            continue

        attr = shader.defaultAssignment.get()
        defaultAssignment = attrToPy(attr)
        mesh_name = defaultAssignment['mesh']
        obj_pattern = "^" + mesh_name + "\d*$"

        shader_hookups[obj_pattern] = shader

    print 'shaders to Hookup: {}'.format(shader_hookups)


    # Apply collected shaders to meshes
    if not meshes:
        meshes = pm.ls(type='mesh')
    # meshnodes = cmds.referenceQuery(reference_node, nodes=True):

    for node in meshes:
        node = pm.listRelatives(node, type='transform',p=True)[0]
        for (obj_pattern, shader) in shader_hookups.iteritems():
            if re.match(obj_pattern, node.name(), re.IGNORECASE):
                # assign the shader to the object
                # cmds.file(unloadReference=reference_node, force=True)
                # cmds.setAttr(reference_node + ".locked", False)
                # cmds.file(loadReference=reference_node)
                pm.select(node, replace=True)
                pm.hyperShade(assign=shader)
                # cmds.file(unloadReference=reference_node)
                # cmds.setAttr(reference_node + ".locked", True)
                # cmds.file(loadReference=reference_node)
            else:
                print "NODE: " + node + " doesn't match " + obj_pattern


def pyToAttr(objAttr, data):
    """
    Write Python data to the given Maya obj.attr.  This data can
    later be read back via attrToPy().

    Arguments:
    objAttr : string : a valid object.attribute name in the scene.  If the
        object exists, but the attribute doesn't, the attribute will be added.
        The if the attribute already exists, it must be of type 'string', so
        the Python data can be written to it.
    data : some Python data :  Data that will be serialised to the attribute
        in question.
    """
    obj, attr = objAttr.split('.')
    # Add the attr if it doesn't exist:
    if not cmds.objExists(objAttr):
        cmds.addAttr(obj, longName=attr, dataType='string')
    # Make sure it is the correct type before modifing:
    if cmds.getAttr(objAttr, type=True) != 'string':
        raise Exception("Object '%s' already has an attribute called '%s', but it isn't type 'string'"%(obj,attr))

    # Serialise the data and return the coresponding string value:
    stringData = json.dumps(data)
    # Make sure attr is unlocked before edit:
    cmds.setAttr(objAttr, edit=True, lock=False)
    # Set attr to string value:
    cmds.setAttr(objAttr, stringData, type='string')
    # And lock it for safety:
    cmds.setAttr(objAttr, edit=True, lock=True)


def attrToPy(objAttr):
    """
    Take previously stored (json) data on a Maya attribute (put there via
    pyToAttr() ) and read it back to valid Python values.

    """
    objAttr = str(objAttr)
    loadedData = json.loads(objAttr)

    return loadedData
