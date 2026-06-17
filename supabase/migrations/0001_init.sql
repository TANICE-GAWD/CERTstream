






create extension if not exists vector;




create table if not exists reg_clauses (
    clause_id    text primary key,
    title        text not null,
    text         text not null,
    jurisdiction text not null,
    source       text not null,
    embedding    vector(384) not null
);


create index if not exists reg_clauses_embedding_idx
    on reg_clauses using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index if not exists reg_clauses_jurisdiction_idx
    on reg_clauses (jurisdiction);




create table if not exists audit_runs (
    audit_id        text primary key,
    document_name   text not null,
    persona         text not null,
    jurisdiction    text not null,
    readiness_score real not null,
    grade           text not null,
    summary         text,
    created_at      timestamptz not null default now()
);

create table if not exists findings (
    id             bigint generated always as identity primary key,
    audit_id       text not null references audit_runs(audit_id) on delete cascade,
    doc_section    text not null,
    claim          text not null,
    clause_id      text not null,
    clause_title   text,
    verdict        text not null,
    severity       text not null,
    rationale      text,
    evidence_quote text,
    recommendation text,
    persona        text not null,
    confidence     real,
    created_at     timestamptz not null default now()
);

create index if not exists findings_audit_idx    on findings (audit_id);
create index if not exists findings_clause_idx   on findings (clause_id);
create index if not exists findings_severity_idx on findings (severity);




create or replace function match_clauses(
    query_embedding     vector(384),
    match_count         int default 6,
    filter_jurisdiction text default null
)
returns table (
    clause_id    text,
    title        text,
    text         text,
    jurisdiction text,
    source       text,
    similarity   float
)
language sql stable as $$
    select
        c.clause_id, c.title, c.text, c.jurisdiction, c.source,
        1 - (c.embedding <=> query_embedding) as similarity
    from reg_clauses c
    where filter_jurisdiction is null or c.jurisdiction = filter_jurisdiction
    order by c.embedding <=> query_embedding
    limit match_count;
$$;


create or replace function severity_breakdown()
returns table (severity text, n bigint)
language sql stable as $$
    select severity, count(*) as n
    from findings
    group by severity
    order by n desc;
$$;
