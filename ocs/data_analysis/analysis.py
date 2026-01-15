import marimo

__generated_with = "0.19.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import duckdb
    import marimo as mo
    import polars as pl
    return duckdb, mo, pl


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
        """
        SELECT
            format('{:t .2f} m^2', sum(surf_parc)) as surface_parc_totale_declaree
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
            o.id,
            o.millesime as millesime_ocs,
            o.code_us,
            o.the_geom as ocs_geom,
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
def _(CODES_US_MAPPING, df_link_filtered, pl):
    pl.concat(
        [
            df_link_filtered.with_columns(
                pl.col("code_us").fill_null(pl.lit("Code US inconnu"))
            )
            .group_by(["id", "code_us"])
            .agg(
                pl.col("geom_intersection_area").sum().alias("surface"),
            ),
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
                .clip(0)
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
    return


if __name__ == "__main__":
    app.run()
