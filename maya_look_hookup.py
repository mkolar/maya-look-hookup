# Code courtesy of shotgun software
import maya.cmds as cmds

def maya_export_shader(obj_name, output_file):

    shading_groups = set()
    shad_group_to_obj = {}
    if cmds.ls(obj_name, dag=True, type="mesh"):
        faces = cmds.polyListComponentConversion(obj_name, toFace=True)
        for shading_group in cmds.listSets(type=1, object=faces[0]):
            shading_groups.add(shading_group)
            shad_group_to_obj[shading_group] = obj_name

            shaders = set()
            script_nodes = []
            for shading_group in list(shading_groups):
                connections = cmds.listConnections(
                    shading_group, source=True, destination=False)
                for shader in cmds.ls(connections, materials=True):

                    shaders.add(shader)
                    obj_name = shad_group_to_obj[shading_group]
                    print obj_name

                    # Instead of using a script node, it would be great to
                    # this data in some other form. Metadata from red9 maybe?
                    script_node = cmds.scriptNode(
                        name="SHADER_HOOKUP_" + obj_name,
                        scriptType=0, # execute on demand.
                        beforeScript=shader,
                    )
                    script_nodes.append(script_node)


            select_nodes = list(shaders)
            #select_nodes.extend(list(shading_groups))
            select_nodes.extend(script_nodes)

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


def hookup_shaders(reference_node):

    hookup_prefix = "SHADER_HOOKUP_"
    shader_hookups = {}
    for node in cmds.ls(type="script"):
        if not node.startswith(hookup_prefix):
            continue
        obj_pattern = node.replace(hookup_prefix, "") + "\d*"
        obj_pattern = "^" + obj_pattern + "$"
        shader = cmds.scriptNode(node, query=True, beforeScript=True)
        shader_hookups[obj_pattern] = shader

    for node in cmds.referenceQuery(reference_node, nodes=True):
        for (obj_pattern, shader) in shader_hookups.iteritems():
            if re.match(obj_pattern, node, re.IGNORECASE):
                # assign the shader to the object
                cmds.file(unloadReference=reference_node, force=True)
                cmds.setAttr(reference_node + ".locked", False)
                cmds.file(loadReference=reference_node)
                cmds.select(node, replace=True)
                cmds.hyperShade(assign=shader)
                cmds.file(unloadReference=reference_node)
                cmds.setAttr(reference_node + ".locked", True)
                cmds.file(loadReference=reference_node)
            else:
                print "NODE: " + node + " doesn't match " + obj_pattern
