import marimo

__generated_with = "0.19.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import re
    import duckdb
    import numpy as np
    import marimo as mo
    import polars as pl
    import plotly.express as px
    import folium
    import shapely
    from pyproj import Transformer
    return Transformer, duckdb, folium, mo, pl, px, re, shapely


@app.cell
def _(duckdb):
    con = duckdb.connect("escosol.duckdb")
    return (con,)


@app.cell
def _(con, mo):
    _ = mo.sql(
        f"""
        LOAD SPATIAL
        """,
        output=False,
        engine=con
    )
    return


@app.cell
def _(con, ign_photovoltaique_sol, mo):
    _ = mo.sql(
        f"""
        SELECT
            sum(surf_parc) as surface_parc_totale_declaree
        from
            ign_photovoltaique_sol
        """,
        engine=con
    )
    return


@app.cell
def _(con, ign_photovoltaique_sol, mo):
    _df = mo.sql(
        f"""
        SELECT
            count(*),
            count(distinct id)
        from ign_photovoltaique_sol
        """,
        engine=con
    )
    return


@app.cell
def _(con, mo, ocs):
    _df = mo.sql(
        f"""
        -- Nombre de lignes dans le jeu de données OCS
        SELECT
            count(*)
        FROM
            ocs
        LIMIT
            5
        """,
        engine=con
    )
    return


@app.cell
def _(con, ign_photovoltaique_sol, mo, ocs):
    df_link = mo.sql(
        f"""
        with
            escosol_projected as (
                SELECT
                    ips.*,
                    -- Projette dans le bon referentiel
                    CASE
                        WHEN LIST_BOOL_OR(
                            LIST_APPLY(ips.insee_com, lambda s: s::text ~ '^971.*|972.*')
                        ) THEN ST_Transform (ips.geom, 'EPSG:4326','EPSG:5490' , true)
                        WHEN LIST_BOOL_OR(
                            LIST_APPLY(ips.insee_com, lambda s: s::text ~ '^973.*')
                        ) THEN ST_Transform (ips.geom, 'EPSG:4326','EPSG:2972' , true)
            			WHEN LIST_BOOL_OR(
                            LIST_APPLY(ips.insee_com, lambda s: s::text ~ '^974.*')
                        ) THEN ST_Transform (ips.geom, 'EPSG:4326','EPSG:2975' , true)
                        WHEN LIST_BOOL_OR(
                            LIST_APPLY(ips.insee_com, lambda s: s::text ~ '^976.*')
                        ) THEN ST_Transform (ips.geom, 'EPSG:4326','EPSG:4471' , true)
                        ELSE ST_Transform (ips.geom, 'EPSG:4326','EPSG:2154' , true)
                    END as geom_proj
                FROM
                    ign_photovoltaique_sol ips
            ),
        escosol_joined as (
        SELECT
            ep.*,
            ST_AsWKB(ep.geom_proj) as geom_proj_wkb,
            o.id,
            o.millesime as millesime_ocs,
            o.code_us,
            o.the_geom as ocs_geom,
            ST_AsWKB(o.the_geom) as ocs_geom_wkb,
            ST_Intersection(ep.geom_proj,o.the_geom) as geom_intersection
        from
            escosol_projected ep
        left join ocs o on ST_INTERSECTS(ep.geom_proj,o.the_geom))
        SELECT
        	ej.*,
            st_area(ej.geom_proj) as project_geom_area,
            st_area(ej.ocs_geom) as ocs_geom_area,
            ST_area(ej.geom_intersection) as geom_intersection_area
        from escosol_joined ej
        """,
        engine=con
    )
    return (df_link,)


@app.cell
def _(df_link, pl):
    # Nombre de parcs pour lesquels on a réussi à trouver au moins une géométrie
    df_link.filter(pl.col("millesime") > pl.col("millesime_ocs")).select(
        ["id","millesime","id_1","millesime_ocs"]
    ).select(pl.col("id").n_unique(),pl.len())
    return


@app.cell
def _(df_link, pl):
    df_link_filtered = df_link.filter(
        (pl.col("millesime") > pl.col("millesime_ocs")) | pl.col("id_1").is_null()
    ).filter(
        (
            pl.col("millesime_ocs")
            .rank(descending=True)
            .over(partition_by=["id", "id_1"], order_by="millesime_ocs")
            == 1
        )
        | pl.col("id_1").is_null()
    )
    return (df_link_filtered,)


@app.cell
def _(df_link_filtered, pl):
    # Verification des surfaces

    df_link_filtered.group_by("id").agg(
        pl.col("insee_com"),
        pl.col("surf_parc").max(),
        pl.col("project_geom_area").max(),
        pl.col("ocs_geom_area"),
        pl.len().alias("num_lines"),
        pl.col("id_1").n_unique().alias("num_unique_ocs_tiles"),
        pl.col("geom_intersection_area").sum(),
    ).with_columns(
        (
            (pl.col("surf_parc") - pl.col("geom_intersection_area"))
            / pl.col("surf_parc")
        ).alias("area_error")
    ).sort(pl.col("area_error").abs(), descending=True)
    return


@app.cell
def _():
    CODES_US_MAPPING = {
        "US1.1": "Agriculture",
        "US1.2": "Sylviculture",
        "US1.3": "Activités d’extraction",
        "US1.4": "Pêche et aquaculture",
        "US1.5": "Autres productions primaires",
        "US2": "Production secondaire",
        "US235": "Usage mixte ",
        "US3": "Production tertiaire",
        "US4.1.1": "Réseaux routiers",
        "US4.1.2": "Réseaux ferrés ",
        "US4.1.3": "Réseaux aériens ",
        "US4.1.4": "Réseaux de transport fluvial et maritime",
        "US4.1.5": "Autres réseaux de transport",
        "US4.2": "Services de logistique et de stockage",
        "US4.3": "Réseaux d'utilité publique",
        "US5": "Usage résidentiel ",
        "US6.1" :"Zones en transition",
        "US6.2": "Zones abandonnées",
        "US6.3": "Sans usage",
        "US6.6": "Usage inconnu ",
    }
    return (CODES_US_MAPPING,)


@app.cell
def _(df_link_filtered, pl):
    df_link_filtered.filter(pl.col("id_1").is_null())
    return


@app.cell
def _(CODES_US_MAPPING, df_link_filtered, pl):
    df_code_us_by_surface = pl.concat(
        [
            df_link_filtered.with_columns(
                pl.col("code_us").fill_null(pl.lit("Code US inconnu"))
            )
            .group_by(["id", "code_us"])
            .agg(
                pl.col("geom_intersection_area").sum().alias("surface"),
            ),
            # Reste de surface sans correspondance avec une géométrie OCS :
            df_link_filtered.with_columns(
                pl.col("code_us").fill_null(pl.lit("Code US inconnu"))
            )
            .group_by(["id"])
            .agg(
                (
                    pl.col("project_geom_area").max()
                    - pl.col("geom_intersection_area").sum()
                )
                .sum()
                .alias("surface"),
            )
            .with_columns(pl.lit("Sans correspondance").alias("code_us"))
            .select(["id", "code_us", "surface"]),
        ],
        how="vertical_relaxed",
    ).group_by("code_us").agg(pl.col("surface").sum()).with_columns(
        pl.col("code_us").replace(CODES_US_MAPPING),
        (100*pl.col("surface")/pl.col("surface").sum()).alias("% de la surface")
    ).sort("surface",descending=True)
    df_code_us_by_surface
    return (df_code_us_by_surface,)


@app.cell
def _(df_code_us_by_surface, px):
    px.bar(
        df_code_us_by_surface,
        x="code_us",
        y="% de la surface",
        template="simple_white",
        text="% de la surface",
        text_auto=".2f",
    )
    return


@app.cell
def _():
    CODES_US_COLOR_MAPPING = {
        "US1.1": "#4269d0",
        "US1.2": "#1f78b4",
        "US1.3": "#b2df8a",
        "US1.4": "#33a02c",
        "US1.5": "#fb9a99",
        "US2": "#e31a1c",
        "US235": "#fdbf6f",
        "US3": "#ff7f00",
        "US6.1" :"#cab2d6",
        "US6.3": "#cab2d6",
    }
    return (CODES_US_COLOR_MAPPING,)


@app.cell
def _(
    CODES_US_COLOR_MAPPING,
    CODES_US_MAPPING,
    Transformer,
    df_link_filtered,
    folium,
    re,
    shapely,
):
    crs_transformers = {
        r"^971.*|972.*": Transformer.from_crs(5490, 4326),
        r"^973.*": Transformer.from_crs(2972, 4326),
        r"^974.*": Transformer.from_crs(2975, 4326),
        r"^976.*": Transformer.from_crs(4471, 4326),
    }

    metropole_transformer = Transformer.from_crs(2154, 4326)


    def project(
        geom: shapely.Geometry, codes_insee: list[str]
    ) -> shapely.Geometry:
        for pattern, transformer in crs_transformers.items():
            if any(re.match(pattern=pattern, string=s) for s in codes_insee):
                return shapely.transform(
                    geom, transformer.transform, interleaved=False
                )

        return shapely.transform(
            geom, metropole_transformer.transform, interleaved=False
        )


    polygons = []
    ids_already_added = []
    for data in df_link_filtered.iter_rows(named=True):
        codes_insee = data["insee_com"]


        ocs_geom_wkb = data["ocs_geom_wkb"]
        if ocs_geom_wkb is not None:
            geom_ocs = shapely.from_wkb(data["ocs_geom_wkb"])
            geom_ocs_4326 = project(geom=geom_ocs, codes_insee=codes_insee)
            color = CODES_US_COLOR_MAPPING.get(data["code_us"],"#b15928")
            description_us = CODES_US_MAPPING.get(data["code_us"],"Inconnu")
            polygon_ocs = folium.Polygon(
                shapely.get_coordinates(geom_ocs_4326),
                fill_color=color,
                stroke=False,
                popup=f"{data["id_1"]} | {description_us} - Surace partagée : {data["geom_intersection_area"]}m^2",
                fill_opacity=0.2,
            )
            polygons.append(polygon_ocs)

        if not data["id"] in ids_already_added:
            geom_photo = shapely.from_wkb(data["geom_proj_wkb"])
            geom_photo_4326 = project(geom=geom_photo, codes_insee=codes_insee)

            polygon_photo = folium.Polygon(
                shapely.get_coordinates(geom_photo_4326),
                popup=f"{data["id"]} | Puisance max :  {data["puiss_max"]} - Surface déclarée : {data["surf_parc"]}",
                fill_color="#f39c12",
                color="#f39c12",
                fill_opacity=0.3,
            
            )
            center = shapely.centroid(geom_photo_4326)
            folium.Marker(tooltip=data["id"],location=[center.x,center.y])
            polygons.append(polygon_photo)
            ids_already_added.append(data["id"])

    return (polygons,)


@app.cell
def _(folium, polygons):
    m = folium.Map(
        location=[46.2, 2.21],
        zoom_start=6,
        tiles="GeoportailFrance.orthos",
    )

    for polygon in polygons:
        polygon.add_to(m)

    m.save("map.html")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
