// Shared function: load one analytics table by name.
// Create as blank query named fn_AnalyticsTable, then paste:

let
    Source = (TableName as text) as table =>
        let
            Db = PostgreSQL.Database(#"PostgreSQL Host", #"PostgreSQL Database"),
            Nav = Db{[Schema = #"PostgreSQL Schema", Item = TableName]}[Data]
        in
            Nav
in
    Source
