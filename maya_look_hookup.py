import pymel.core as pm
import json
from pprint import pprint


def export_shaders(nodes, look_name, output_file):

    shading_groups = set()
    shaders = set()

    for node in nodes:
        shape = node.getShape()
        if shape:
            faces = pm.polyListComponentConversion(shape, toFace=True)
            for shading_group in pm.listSets(type=1, object=faces[0]):
                shading_groups.add(shading_group)
                connections = pm.listConnections(
                    shading_group, source=True, destination=False)
                for shader in pm.ls(connections, materials=True):
                    try:
                        shaderAttr = pm.Attribute('{}.shaderAssignment'.format(shader))
                        shaderAttr.unlock()
                        pm.deleteAttr(shaderAttr)
                    except:
                        pass

    for node in nodes:
        print "Processed mesh: " + node
        shape = node.getShape()
        if shape:
            faces = pm.polyListComponentConversion(shape, toFace=True)
            for shading_group in pm.listSets(type=1, object=faces[0]):
                shading_groups.add(shading_group)

                connections = pm.listConnections(
                    shading_group, source=True, destination=False)

                for shader in pm.ls(connections, materials=True):
                    shaders.add(shader)

                    shaderAttr = '{}.shaderAssignment'.format(shader)

                    assignData = {'assetid': []}
                    if pm.objExists(shaderAttr):
                        attr = pm.Attribute(shaderAttr)
                        try:
                            assignData = json.loads(attr.get())
                        except:
                            pass
                        assignData['assetid'].append(node.assetid.get())
                    else:
                        assignData['assetid'].append(node.assetid.get())

                    # Store data to our node:
                    jsonToAttr(shaderAttr, assignData)

    select_nodes = list(shading_groups)

    asset = export_render_attributes(nodes, look_name)

    pm.select(select_nodes, replace=True, ne=True)
    pm.select(asset, add=1)

    # write a .ma file to the publish path with the shader network definitions
    pm.exportSelected(
        output_file,
        type='mayaAscii',
        shader=True,
        force=True
        )

    return select_nodes


def export_render_attributes(nodes, name):
    attr_filter = ['castsShadows',
                    'receiveShadows',
                    'visibleInReflections',
                    'visibleInRefractions',
                    'doubleSided',
                    'yetiSubdivision',
                    'yetiSubdivisionIterations'
                    ]

    object_list = []

    for node in nodes:
        shape = node.getShape()
        object_collection = {'transform': node.name(),
                             'shape': shape.name(),
                             'assetid': node.assetid.get(),
                             'attributes': {}
                             }
        if shape:
            for attr in shape.listAttr():
                attr_name = attr.split('.')[1]
                if attr_name in attr_filter or attr_name.startswith('ai'):
                    object_collection['attributes'][attr_name] = attr.get()
        object_list.append(object_collection)

    asset = pm.createNode('container', n=name)
    json_attr = '{}.lookAttributes'.format(asset)
    pprint(object_list)
    jsonToAttr(json_attr, object_list)

    return asset


def hookup_shaders(nodes=None, shaders=None):

    if not shaders:
        shaders = pm.ls(materials=True)

    # Apply collected shaders to meshes
    meshes = []
    if nodes:
        for node in nodes:
            meshes.append(node.listRelatives(type='mesh'))
    else:
        meshes = pm.ls(type='mesh')

    # get all shaders
    for shader in shaders:
        # filter out shaders with shaderAsisgnment
        if not shader.hasAttr('shaderAssignment'):
            continue

        shaderAssignment = json.loads(shader.shaderAssignment.get())
        print shaderAssignment
        for key in shaderAssignment:
            for mesh in meshes:
                transform = pm.listRelatives(mesh, type='transform', p=True)[0]
                if transform.hasAttr(key):
                    for mesh_to_assign in shaderAssignment[key]:
                        if transform.attr(key).get() == mesh_to_assign:
                            print transform
                            pm.select(transform, replace=True)
                            pm.hyperShade(assign=shader)
            print shaderAssignment[key]

def hookup_render_attributes(nodes=None):
    looks = pm.ls(containers=True)

    meshes = []

    for look in looks:
        if look.hasAttr('lookAttributes'):
            look_attributes = json.loads(look.lookAttributes.get())
            for subset in look_attributes:
                for node in nodes:
                    shape = node.getShape()
                    if (node.hasAttr('assetid') and node.assetid.get() == subset['assetid']):
                        for a in subset['attributes']:
                            if shape.hasAttr(a):
                                shape.attr(a).set(subset['attributes'][a])


def jsonToAttr(objAttr, data):

    obj, attr = objAttr.split('.')
    # Add the attr if it doesn't exist:
    if not pm.objExists(objAttr):
        pm.addAttr(obj, longName=attr, dataType='string')
    # Make sure it is the correct type before modifing:
    if pm.getAttr(objAttr, type=True) != 'string':
        raise Exception("Object '{}' already has an attribute called '{}', but it isn't type 'string'".format(obj,attr))

    stringData = json.dumps(data)
    pm.setAttr(objAttr, edit=True, lock=False)
    pm.setAttr(objAttr, stringData, type='string')
    pm.setAttr(objAttr, edit=True, lock=True)
