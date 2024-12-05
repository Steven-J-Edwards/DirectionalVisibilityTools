import arcpy
import os

def generate_individual_viewsheds(dem, observer_layer, observer_offsets, outer_radius, use_atmospheric_refraction):
    """
    Generate individual viewsheds for each observer point and offset, with unique output names.

    Parameters:
    - dem (str): Path to the DEM raster layer.
    - observer_layer (str): Path to the point feature layer containing observer locations.
    - observer_offsets (list): List of observer offsets (in meters) to model.
    - outer_radius (float): Outer radius parameter for the viewshed analysis.
    - use_atmospheric_refraction (bool): Whether to use atmospheric refraction.
    """
    # Ensure the current workspace is set to the default geodatabase
    current_gdb = arcpy.env.workspace or arcpy.env.scratchGDB

    if not current_gdb:
        raise RuntimeError("No current geodatabase is set.")

    # Convert observer offsets to floats if provided as strings
    observer_offsets = [float(offset) for offset in observer_offsets]

    # Check if the SiteID field exists; if not, create and populate it
    fields = [field.name for field in arcpy.ListFields(observer_layer)]
    if "SiteID" not in fields:
        print("Adding 'SiteID' field to observer layer...")
        arcpy.AddField_management(observer_layer, "SiteID", "LONG")
        with arcpy.da.UpdateCursor(observer_layer, ["OBJECTID", "SiteID"]) as cursor:
            for row in cursor:
                row[1] = row[0]  # Assign OBJECTID to SiteID
                cursor.updateRow(row)
        print("'SiteID' field added and populated successfully.")

    # Iterate through each observer point
    with arcpy.da.SearchCursor(observer_layer, ["SiteID", "SHAPE@"]) as cursor:
        for row in cursor:
            site_id = row[0]  # Get the SiteID
            observer_geometry = row[1]  # Get the geometry of the observer point

            # Create a temporary layer for the current observer point
            temp_layer = "temp_observer_layer"
            arcpy.MakeFeatureLayer_management(observer_layer, temp_layer, f"SiteID = {site_id}")

            # Iterate through the observer offsets
            for offset in observer_offsets:
                # Generate the output name based on the SiteID and offset
                output_name = f"vshed_{site_id}_{int(offset)}m"

                # Create the full path for the output raster
                output_path = os.path.join(current_gdb, output_name)

                # Print/log the process
                arcpy.AddMessage(f"Calculating viewshed for SiteID {site_id} with observer offset {offset}m...")
                print(f"Calculating viewshed for SiteID {site_id} with observer offset {offset}m...")

                try:
                    # Perform the Viewshed2 analysis
                    output_raster = arcpy.sa.Viewshed2(
                        in_raster=dem,
                        in_observer_features=temp_layer,
                        analysis_type="FREQUENCY",  # Default, to calculate visibility frequency
                        refractivity_coefficient=0.13 if use_atmospheric_refraction else 0,
                        surface_offset=0,  # Optional, can be set if required
                        observer_offset=offset,  # Correct parameter for observer height
                        outer_radius=outer_radius,  # Outer radius for visibility calculation
                    )

                    # Save the output raster to the current geodatabase
                    output_raster.save(output_path)

                    # Log the output
                    arcpy.AddMessage(f"Viewshed created: {output_path}")
                    print(f"Viewshed created: {output_path}")

                except Exception as e:
                    arcpy.AddError(f"Failed to calculate viewshed for SiteID {site_id} at offset {offset}: {e}")
                    print(f"Failed to calculate viewshed for SiteID {site_id} at offset {offset}: {e}")

            # Clean up the temporary layer
            arcpy.Delete_management(temp_layer)

    arcpy.AddMessage("All viewsheds generated successfully.")
    print("All viewsheds generated successfully.")

# Main function to fetch parameters from the user
if __name__ == "__main__":
    try:
        # Get user inputs
        dem_input = arcpy.GetParameterAsText(0)  # DEM raster
        observer_input = arcpy.GetParameterAsText(1)  # Observer point layer
        observer_offsets_input = arcpy.GetParameterAsText(2)  # List of observer offsets (semicolon-separated)
        outer_radius = float(arcpy.GetParameterAsText(3))  # Outer radius
        use_atmospheric_refraction = arcpy.GetParameter(4)  # Boolean: Use atmospheric refraction

        # Convert the observer offsets from a semicolon-separated string to a list
        observer_offsets = observer_offsets_input.split(";") if observer_offsets_input else []
        observer_offsets = [float(offset) for offset in observer_offsets]  # Convert to floats

        # Validate inputs
        if not dem_input or not observer_input:
            raise ValueError("Both DEM and Observer inputs are required.")
        if not observer_offsets:
            raise ValueError("At least one observer offset must be provided.")

        # Set the current workspace (to ensure outputs go to the current GDB)
        arcpy.env.workspace = arcpy.env.workspace or arcpy.env.scratchGDB

        # Call the function to generate individual viewsheds
        generate_individual_viewsheds(
            dem=dem_input,
            observer_layer=observer_input,
            observer_offsets=observer_offsets,
            outer_radius=outer_radius,
            use_atmospheric_refraction=use_atmospheric_refraction
        )

    except Exception as e:
        # Log and raise errors
        arcpy.AddError(f"Script failed: {e}")
        print(f"Script failed: {e}")
        raise
