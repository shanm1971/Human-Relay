--
-- PostgreSQL database dump
--

\restrict JrIBwsDfVCYwZbIoAvU6NTvweTH6eG4gX0YsESzIxKJeVYBJEEIc2HCbpeqgNVZ

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: relay_immutable(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.relay_immutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
                BEGIN RAISE EXCEPTION 'append-only record'; END; $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_permissions (
    id character varying NOT NULL,
    agent_id character varying NOT NULL,
    capability character varying NOT NULL,
    allowed boolean NOT NULL,
    max_price integer NOT NULL,
    created_at double precision
);


--
-- Name: agents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents (
    id character varying NOT NULL,
    organization_id character varying NOT NULL,
    display_name character varying NOT NULL,
    description character varying,
    status character varying NOT NULL,
    api_key_hash character varying NOT NULL,
    max_task_price integer NOT NULL,
    hourly_limit integer NOT NULL,
    daily_limit integer NOT NULL,
    monthly_limit integer NOT NULL,
    max_concurrent_tasks integer NOT NULL,
    max_session_messages integer NOT NULL,
    max_revision_requests integer NOT NULL,
    created_at double precision NOT NULL,
    updated_at double precision,
    last_seen_at double precision
);


--
-- Name: audit_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_events (
    id character varying NOT NULL,
    organization_id character varying,
    agent_id character varying,
    worker_id character varying,
    task_id character varying,
    request_id character varying,
    event_type character varying NOT NULL,
    event_data_json json NOT NULL,
    created_at double precision NOT NULL
);


--
-- Name: credit_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credit_transactions (
    id character varying NOT NULL,
    organization_id character varying NOT NULL,
    agent_id character varying,
    worker_id character varying,
    task_id character varying,
    offer_id character varying,
    type character varying NOT NULL,
    amount integer NOT NULL,
    status character varying NOT NULL,
    dedupe_key character varying NOT NULL,
    created_at double precision NOT NULL
);


--
-- Name: identities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.identities (
    id character varying NOT NULL,
    role character varying NOT NULL,
    status character varying NOT NULL,
    country character varying NOT NULL,
    CONSTRAINT identities_country_check CHECK (((country)::text = 'US'::text)),
    CONSTRAINT identities_role_check CHECK (((role)::text = ANY ((ARRAY['principal'::character varying, 'worker'::character varying, 'admin'::character varying])::text[])))
);


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organizations (
    id character varying NOT NULL,
    name character varying NOT NULL,
    status character varying NOT NULL,
    credit_balance integer NOT NULL,
    reserved integer NOT NULL,
    created_at double precision NOT NULL,
    updated_at double precision,
    CONSTRAINT organizations_check CHECK (((credit_balance >= 0) AND (reserved >= 0) AND (reserved <= credit_balance)))
);


--
-- Name: principals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.principals (
    id character varying NOT NULL,
    organization_id character varying NOT NULL,
    user_id character varying NOT NULL,
    role character varying,
    created_at double precision
);


--
-- Name: task_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_messages (
    id character varying NOT NULL,
    task_id character varying NOT NULL,
    sender_type character varying NOT NULL,
    sender_id character varying NOT NULL,
    message_type character varying NOT NULL,
    content_json json NOT NULL,
    created_at double precision NOT NULL
);


--
-- Name: task_offers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_offers (
    id character varying NOT NULL,
    agent_id character varying NOT NULL,
    worker_id character varying NOT NULL,
    capability character varying NOT NULL,
    objective character varying NOT NULL,
    instructions character varying NOT NULL,
    context_json json NOT NULL,
    response_schema_json json NOT NULL,
    offered_price integer NOT NULL,
    deadline_at double precision NOT NULL,
    max_revisions integer NOT NULL,
    status character varying NOT NULL,
    idempotency_key character varying NOT NULL,
    payload_hash character varying NOT NULL,
    created_at double precision NOT NULL,
    accepted_at double precision,
    declined_at double precision,
    expired_at double precision,
    CONSTRAINT task_offers_offered_price_check CHECK (((offered_price >= 100) AND (offered_price <= 2000)))
);


--
-- Name: task_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_results (
    id character varying NOT NULL,
    task_id character varying NOT NULL,
    worker_id character varying NOT NULL,
    result_json json NOT NULL,
    schema_valid boolean NOT NULL,
    submitted_at double precision NOT NULL,
    accepted_at double precision,
    rejected_at double precision
);


--
-- Name: tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tasks (
    id character varying NOT NULL,
    task_offer_id character varying NOT NULL,
    organization_id character varying NOT NULL,
    agent_id character varying NOT NULL,
    worker_id character varying NOT NULL,
    capability character varying NOT NULL,
    status character varying NOT NULL,
    price integer NOT NULL,
    revision_count integer NOT NULL,
    intervention boolean NOT NULL,
    failure_reason character varying,
    session_opened_at double precision NOT NULL,
    completed_at double precision,
    failed_at double precision,
    created_at double precision NOT NULL,
    updated_at double precision
);


--
-- Name: worker_capabilities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.worker_capabilities (
    id character varying NOT NULL,
    worker_id character varying NOT NULL,
    capability character varying NOT NULL,
    verification_level character varying,
    minimum_price integer NOT NULL,
    enabled boolean NOT NULL,
    created_at double precision
);


--
-- Name: worker_earnings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.worker_earnings (
    id character varying NOT NULL,
    worker_id character varying NOT NULL,
    task_id character varying NOT NULL,
    gross_amount integer NOT NULL,
    platform_fee integer NOT NULL,
    net_amount integer NOT NULL,
    status character varying NOT NULL,
    created_at double precision
);


--
-- Name: workers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workers (
    id character varying NOT NULL,
    user_id character varying NOT NULL,
    public_worker_id character varying,
    status character varying NOT NULL,
    availability character varying NOT NULL,
    minimum_task_price integer NOT NULL,
    maximum_active_tasks integer NOT NULL,
    quality_score double precision NOT NULL,
    tasks_completed integer NOT NULL,
    tasks_failed integer NOT NULL,
    schema_attempts integer NOT NULL,
    schema_valid integer NOT NULL,
    created_at double precision,
    updated_at double precision
);


--
-- Name: agent_permissions agent_permissions_agent_id_capability_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_permissions
    ADD CONSTRAINT agent_permissions_agent_id_capability_key UNIQUE (agent_id, capability);


--
-- Name: agent_permissions agent_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_permissions
    ADD CONSTRAINT agent_permissions_pkey PRIMARY KEY (id);


--
-- Name: agents agents_api_key_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_api_key_hash_key UNIQUE (api_key_hash);


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: audit_events audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_pkey PRIMARY KEY (id);


--
-- Name: credit_transactions credit_transactions_dedupe_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_dedupe_key_key UNIQUE (dedupe_key);


--
-- Name: credit_transactions credit_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_pkey PRIMARY KEY (id);


--
-- Name: identities identities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.identities
    ADD CONSTRAINT identities_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: principals principals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.principals
    ADD CONSTRAINT principals_pkey PRIMARY KEY (id);


--
-- Name: principals principals_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.principals
    ADD CONSTRAINT principals_user_id_key UNIQUE (user_id);


--
-- Name: task_messages task_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_messages
    ADD CONSTRAINT task_messages_pkey PRIMARY KEY (id);


--
-- Name: task_offers task_offers_agent_id_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_offers
    ADD CONSTRAINT task_offers_agent_id_idempotency_key_key UNIQUE (agent_id, idempotency_key);


--
-- Name: task_offers task_offers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_offers
    ADD CONSTRAINT task_offers_pkey PRIMARY KEY (id);


--
-- Name: task_results task_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_results
    ADD CONSTRAINT task_results_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_task_offer_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_task_offer_id_key UNIQUE (task_offer_id);


--
-- Name: worker_capabilities worker_capabilities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.worker_capabilities
    ADD CONSTRAINT worker_capabilities_pkey PRIMARY KEY (id);


--
-- Name: worker_capabilities worker_capabilities_worker_id_capability_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.worker_capabilities
    ADD CONSTRAINT worker_capabilities_worker_id_capability_key UNIQUE (worker_id, capability);


--
-- Name: worker_earnings worker_earnings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.worker_earnings
    ADD CONSTRAINT worker_earnings_pkey PRIMARY KEY (id);


--
-- Name: worker_earnings worker_earnings_task_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.worker_earnings
    ADD CONSTRAINT worker_earnings_task_id_key UNIQUE (task_id);


--
-- Name: workers workers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workers
    ADD CONSTRAINT workers_pkey PRIMARY KEY (id);


--
-- Name: workers workers_public_worker_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workers
    ADD CONSTRAINT workers_public_worker_id_key UNIQUE (public_worker_id);


--
-- Name: workers workers_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workers
    ADD CONSTRAINT workers_user_id_key UNIQUE (user_id);


--
-- Name: ix_task_offers_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_task_offers_agent_id ON public.task_offers USING btree (agent_id);


--
-- Name: ix_task_offers_deadline_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_task_offers_deadline_at ON public.task_offers USING btree (deadline_at);


--
-- Name: ix_task_offers_worker_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_task_offers_worker_id ON public.task_offers USING btree (worker_id);


--
-- Name: audit_events immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER immutable BEFORE DELETE OR UPDATE ON public.audit_events FOR EACH ROW EXECUTE FUNCTION public.relay_immutable();


--
-- Name: credit_transactions immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER immutable BEFORE DELETE OR UPDATE ON public.credit_transactions FOR EACH ROW EXECUTE FUNCTION public.relay_immutable();


--
-- Name: worker_earnings immutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER immutable BEFORE DELETE OR UPDATE ON public.worker_earnings FOR EACH ROW EXECUTE FUNCTION public.relay_immutable();


--
-- Name: agent_permissions agent_permissions_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_permissions
    ADD CONSTRAINT agent_permissions_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: agents agents_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: credit_transactions credit_transactions_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: credit_transactions credit_transactions_offer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_offer_id_fkey FOREIGN KEY (offer_id) REFERENCES public.task_offers(id);


--
-- Name: credit_transactions credit_transactions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: credit_transactions credit_transactions_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: credit_transactions credit_transactions_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_transactions
    ADD CONSTRAINT credit_transactions_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.workers(id);


--
-- Name: principals principals_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.principals
    ADD CONSTRAINT principals_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: principals principals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.principals
    ADD CONSTRAINT principals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.identities(id);


--
-- Name: task_messages task_messages_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_messages
    ADD CONSTRAINT task_messages_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: task_offers task_offers_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_offers
    ADD CONSTRAINT task_offers_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: task_offers task_offers_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_offers
    ADD CONSTRAINT task_offers_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.workers(id);


--
-- Name: task_results task_results_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_results
    ADD CONSTRAINT task_results_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: task_results task_results_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_results
    ADD CONSTRAINT task_results_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.workers(id);


--
-- Name: tasks tasks_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: tasks tasks_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id);


--
-- Name: tasks tasks_task_offer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_task_offer_id_fkey FOREIGN KEY (task_offer_id) REFERENCES public.task_offers(id);


--
-- Name: tasks tasks_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.workers(id);


--
-- Name: worker_capabilities worker_capabilities_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.worker_capabilities
    ADD CONSTRAINT worker_capabilities_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.workers(id);


--
-- Name: worker_earnings worker_earnings_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.worker_earnings
    ADD CONSTRAINT worker_earnings_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id);


--
-- Name: worker_earnings worker_earnings_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.worker_earnings
    ADD CONSTRAINT worker_earnings_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.workers(id);


--
-- Name: workers workers_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workers
    ADD CONSTRAINT workers_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.identities(id);


--
-- Name: agent_permissions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.agent_permissions ENABLE ROW LEVEL SECURITY;

--
-- Name: agents; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;

--
-- Name: audit_events; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;

--
-- Name: credit_transactions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;

--
-- Name: identities; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.identities ENABLE ROW LEVEL SECURITY;

--
-- Name: organizations; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;

--
-- Name: principals; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.principals ENABLE ROW LEVEL SECURITY;

--
-- Name: task_messages; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.task_messages ENABLE ROW LEVEL SECURITY;

--
-- Name: task_offers; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.task_offers ENABLE ROW LEVEL SECURITY;

--
-- Name: task_results; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.task_results ENABLE ROW LEVEL SECURITY;

--
-- Name: tasks; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;

--
-- Name: worker_capabilities; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.worker_capabilities ENABLE ROW LEVEL SECURITY;

--
-- Name: worker_earnings; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.worker_earnings ENABLE ROW LEVEL SECURITY;

--
-- Name: workers; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.workers ENABLE ROW LEVEL SECURITY;

--
-- PostgreSQL database dump complete
--

\unrestrict JrIBwsDfVCYwZbIoAvU6NTvweTH6eG4gX0YsESzIxKJeVYBJEEIc2HCbpeqgNVZ
