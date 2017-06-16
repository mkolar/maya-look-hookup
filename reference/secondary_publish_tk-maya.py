# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import re
import shutil
import maya.cmds as cmds
import maya.mel as mel

import tank
from tank import Hook
from tank import TankError

class PublishHook(Hook):
    """
    Single hook that implements publish functionality for secondary tasks
    """    
    def execute(self, tasks, work_template, comment, thumbnail_path, sg_task, primary_task, primary_publish_path, progress_cb, **kwargs):
        """
        Main hook entry point
        :param tasks:                   List of secondary tasks to be published.  Each task is a 
                                        dictionary containing the following keys:
                                        {
                                            item:   Dictionary
                                                    This is the item returned by the scan hook 
                                                    {   
                                                        name:           String
                                                        description:    String
                                                        type:           String
                                                        other_params:   Dictionary
                                                    }
                                                   
                                            output: Dictionary
                                                    This is the output as defined in the configuration - the 
                                                    primary output will always be named 'primary' 
                                                    {
                                                        name:             String
                                                        publish_template: template
                                                        tank_type:        String
                                                    }
                                        }
                        
        :param work_template:           template
                                        This is the template defined in the config that
                                        represents the current work file
               
        :param comment:                 String
                                        The comment provided for the publish
                        
        :param thumbnail:               Path string
                                        The default thumbnail provided for the publish
                        
        :param sg_task:                 Dictionary (shotgun entity description)
                                        The shotgun task to use for the publish    
                        
        :param primary_publish_path:    Path string
                                        This is the path of the primary published file as returned
                                        by the primary publish hook
                        
        :param progress_cb:             Function
                                        A progress callback to log progress during pre-publish.  Call:
                                        
                                            progress_cb(percentage, msg)
                                             
                                        to report progress to the UI
                        
        :param primary_task:            The primary task that was published by the primary publish hook.  Passed
                                        in here for reference.  This is a dictionary in the same format as the
                                        secondary tasks above.
        
        :returns:                       A list of any tasks that had problems that need to be reported 
                                        in the UI.  Each item in the list should be a dictionary containing 
                                        the following keys:
                                        {
                                            task:   Dictionary
                                                    This is the task that was passed into the hook and
                                                    should not be modified
                                                    {
                                                        item:...
                                                        output:...
                                                    }
                                                    
                                            errors: List
                                                    A list of error messages (strings) to report    
                                        }
        """
        results = []
        
        # publish all tasks:
        for task in tasks:
            item = task["item"]
            output = task["output"]
            errors = []
        
            # report progress:
            progress_cb(0, "Publishing", task)

            # publish alembic_cache output
            if output["name"] == "alembic_cache":
                try:
                   self.__publish_alembic_cache(item, output, work_template,
                       primary_publish_path, sg_task, comment, thumbnail_path,
                       progress_cb)
                except Exception, e:
                   errors.append("Publish failed - %s" % e)
            elif output["name"] == "camera":
                try:
                   self.__publish_camera(item, output, work_template,
                       primary_publish_path, sg_task, comment, thumbnail_path,
                       progress_cb)
                except Exception, e:
                   errors.append("Publish failed - %s" % e)
            elif output["name"] == "maya_shader_network":
                try:
                   self.__publish_maya_shader_network(item, output,
                       work_template, primary_publish_path, sg_task, comment,
                       thumbnail_path, progress_cb)
                except Exception, e:
                   errors.append("Publish failed - %s" % e)
            else:
                # don't know how to publish this output types!
                errors.append("Don't know how to publish this item!")

            # if there is anything to report then add to result
            if len(errors) > 0:
                # add result:
                results.append({"task":task, "errors":errors})
             
            progress_cb(100)
             
        return results

    def __publish_alembic_cache(self, item, output, work_template, primary_publish_path, 
                                        sg_task, comment, thumbnail_path, progress_cb):
        """
        Publish an Alembic cache file for the scene and publish it to Shotgun.
        
        :param item:                    The item to publish
        :param output:                  The output definition to publish with
        :param work_template:           The work template for the current scene
        :param primary_publish_path:    The path to the primary published file
        :param sg_task:                 The Shotgun task we are publishing for
        :param comment:                 The publish comment/description
        :param thumbnail_path:          The path to the publish thumbnail
        :param progress_cb:             A callback that can be used to report progress
        """
        # Determine the publish info to use.
        progress_cb(10, "Determining publish details")

        # Get the current scene path and extract fields from it
        # using the work template.
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        short_name = cmds.ls(item["name"], shortNames=True)[0]
        fields["grp_name"] = short_name
        tank_type = output["tank_type"]
                
        # Create the publish path by applying the fields 
        # with the publish template.
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields)
        
        # Ensure the publish folder exists.
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # Determine the publish name.
        publish_name = fields.get("name") + '_' + short_name
        if not publish_name:
            publish_name = os.path.basename(publish_path)
        
        progress_cb(10, "Analysing scene")

        # Set the alembic args that make the most sense when working with Mari.  These flags
        # will ensure the export of an Alembic file that contains all visible geometry from
        # the current scene together with UV's and face sets for use in Mari.
        alembic_args = [
            '-renderableOnly',
            '-writeFaceSets',
            '-uvWrite',
            '-file ' + publish_path.replace('\\', '/'),
            '-selection',
        ]

        # Find the animated frame range to use.
        start_frame, end_frame = self._find_scene_animation_range()
        if start_frame and end_frame:
            alembic_args.append('-fr %d %d' % (start_frame, end_frame))

        # Select the nodes we're going to export.
        cmds.select(item['name'], hierarchy=True)

        # Build the export command.  Note, use AbcExport -help in Maya for
        # more detailed Alembic export help.
        abc_export_cmd = ("AbcExport -j \"%s\"" % " ".join(alembic_args))
        progress_cb(30, "Exporting Alembic cache")
        try:
            self.parent.log_debug("Executing command: %s" % abc_export_cmd)
            cmds.AbcExport(j=' '.join(alembic_args))
        except Exception as e:
            raise TankError("Failed to export Alembic Cache: %s" % e)

        # Register the publish.
        progress_cb(75, "Registering the publish")        
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": [primary_publish_path],
            "published_file_type":tank_type
        }
        tank.util.register_publish(**args)

    def __publish_camera(self, item, output, work_template,
        primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
        """
        Publish a shot camera and register with Shotgun.
        
        :param item:                    The item to publish
        :param output:                  The output definition to publish with
        :param work_template:           The work template for the current scene
        :param primary_publish_path:    The path to the primary published file
        :param sg_task:                 The Shotgun task we are publishing for
        :param comment:                 The publish comment/description
        :param thumbnail_path:          The path to the publish thumbnail
        :param progress_cb:             A callback that can be used to report progress
        """

        # determine the publish info to use
        #
        progress_cb(10, "Determining publish details")

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        tank_type = output["tank_type"]
        cam_name = item['name']
        fields['obj_name'] = cam_name
        fields['name'] = re.sub(r'[\W_]+', '', cam_name)
                
        # create the publish path by applying the fields 
        # with the publish template:
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields)
        
        # ensure the publish folder exists:
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # determine the publish name:
        publish_name = fields.get("obj_name")
        if not publish_name:
            publish_name = os.path.basename(publish_path)
        
        # Find additional info from the scene:
        #
        progress_cb(10, "Analysing scene")

        cmds.select(cam_name, replace=True)

        # write a .ma file to the publish path with the camera definitions
        progress_cb(25, "Exporting the camera.")        
        cmds.file(publish_path, type='mayaAscii', exportSelected=True,
            options="v=0", prompt=False, force=True)

        # register the publish:
        progress_cb(75, "Registering the publish")        
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": [primary_publish_path],
            "published_file_type":tank_type
        }
        tank.util.register_publish(**args)

    def __publish_maya_shader_network(self, item, output, work_template, primary_publish_path, 
                                        sg_task, comment, thumbnail_path, progress_cb):
        """
        Publish shader networks for the asset and register with Shotgun.
        
        :param item:                    The item to publish
        :param output:                  The output definition to publish with
        :param work_template:           The work template for the current scene
        :param primary_publish_path:    The path to the primary published file
        :param sg_task:                 The Shotgun task we are publishing for
        :param comment:                 The publish comment/description
        :param thumbnail_path:          The path to the publish thumbnail
        :param progress_cb:             A callback that can be used to report progress
        """

        # determine the publish info to use
        #
        progress_cb(10, "Determining publish details")

        # get the current scene path and extract fields from it
        # using the work template:
        scene_path = os.path.abspath(cmds.file(query=True, sn=True))
        fields = work_template.get_fields(scene_path)
        publish_version = fields["version"]
        tank_type = output["tank_type"]
        obj_name = item['name']
        fields['obj_name'] = obj_name
        fields['name'] = re.sub(r'[\W_]+', '', obj_name)

        # create the publish path by applying the fields 
        # with the publish template:
        publish_template = output["publish_template"]
        publish_path = publish_template.apply_fields(fields)
        
        # ensure the publish folder exists:
        publish_folder = os.path.dirname(publish_path)
        self.parent.ensure_folder_exists(publish_folder)

        # determine the publish name:
        publish_name = fields.get("obj_name")
        if not publish_name:
            publish_name = os.path.basename(publish_path)
        
        # Find additional info from the scene:
        #
        progress_cb(10, "Analysing scene")

        # clean up any hookup nodes that existed before
        _clean_shader_hookup_script_nodes()

        # there's probably a better way to do this. i am jon snow (i know
        # nothing)
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

                # can't seem to store arbitrary data in maya in any
                # reasonable way. would love to know a better way to 
                # do this. for now, just create a script node that 
                # we can easily find and deduce an object name and
                # shader name. Yes, this is hacky.
                script_node = cmds.scriptNode(
                    name="SHADER_HOOKUP_" + obj_name,
                    scriptType=0, # execute on demand.
                    beforeScript=shader,
                )
                script_nodes.append(script_node)

        if not shaders:
            progress_cb(100, "No shader networks to export.")        
            return

        select_nodes = list(shaders)
        #select_nodes.extend(list(shading_groups))
        select_nodes.extend(script_nodes)

        cmds.select(select_nodes, replace=True)

        # write a .ma file to the publish path with the shader network definitions
        progress_cb(25, "Exporting the shader network.")        
        cmds.file(
            publish_path,
            type='mayaAscii',
            exportSelected=True,
            options="v=0",
            prompt=False,
            force=True
        )

        # clean up shader hookup nodes. they should exist in the publish file
        # only.
        _clean_shader_hookup_script_nodes()

        # register the publish:
        progress_cb(75, "Registering the publish")        
        args = {
            "tk": self.parent.tank,
            "context": self.parent.context,
            "comment": comment,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": thumbnail_path,
            "task": sg_task,
            "dependency_paths": [primary_publish_path],
            "published_file_type":tank_type
        }
        tank.util.register_publish(**args)

    def _find_scene_animation_range(self):
        """
        Find the animation range from the current scene.
        """
        # look for any animation in the scene:
        animation_curves = cmds.ls(typ="animCurve")
        
        # if there aren't any animation curves then just return
        # a single frame:
        if not animation_curves:
            return (1, 1)
        
        # something in the scene is animated so return the
        # current timeline.  This could be extended if needed
        # to calculate the frame range of the animated curves.
        start = int(cmds.playbackOptions(q=True, min=True))
        end = int(cmds.playbackOptions(q=True, max=True))        
        
        return (start, end)


def _clean_shader_hookup_script_nodes():

    # clean up any existing shader hookup nodes
    hookup_prefix = "SHADER_HOOKUP_"
    shader_hookups = {}
    for node in cmds.ls(type="script"):
        if node.startswith(hookup_prefix):
            cmds.delete(node)

