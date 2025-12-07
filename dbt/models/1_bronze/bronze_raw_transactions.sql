SELECT * -- noqa: AM04
FROM
    READ_JSON(
        's3://oking-personal-finances/extracts/gocardless/73ed675f-12fe-4d85-88d3-d439976ec662/**/*.json',
        auto_detect = true,
        union_by_name = true
    )
