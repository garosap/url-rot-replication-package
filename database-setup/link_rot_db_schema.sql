--
-- PostgreSQL database dump
--

-- Dumped from database version 14.18 (Ubuntu 14.18-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.18 (Ubuntu 14.18-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: agaros; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA agaros;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: paper_urls; Type: TABLE; Schema: agaros; Owner: -
--

CREATE TABLE agaros.paper_urls (
    paper_id integer NOT NULL,
    url_id integer NOT NULL
);


--
-- Name: papers; Type: TABLE; Schema: agaros; Owner: -
--

CREATE TABLE agaros.papers (
    id integer NOT NULL,
    venue_id integer,
    year integer,
    ee character varying(500),
    doi text
);


--
-- Name: papers_id_seq; Type: SEQUENCE; Schema: agaros; Owner: -
--

CREATE SEQUENCE agaros.papers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: papers_id_seq; Type: SEQUENCE OWNED BY; Schema: agaros; Owner: -
--

ALTER SEQUENCE agaros.papers_id_seq OWNED BY agaros.papers.id;


--
-- Name: urls; Type: TABLE; Schema: agaros; Owner: -
--

CREATE TABLE agaros.urls (
    id integer NOT NULL,
    url character varying(500) NOT NULL,
    active boolean,
    status_code integer DEFAULT 0,
    network_error integer,
    section character varying(500)
);


--
-- Name: urls_id_seq; Type: SEQUENCE; Schema: agaros; Owner: -
--

CREATE SEQUENCE agaros.urls_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: urls_id_seq; Type: SEQUENCE OWNED BY; Schema: agaros; Owner: -
--

ALTER SEQUENCE agaros.urls_id_seq OWNED BY agaros.urls.id;


--
-- Name: venues; Type: TABLE; Schema: agaros; Owner: -
--

CREATE TABLE agaros.venues (
    id integer NOT NULL,
    acronym character varying(20) NOT NULL,
    name character varying(200),
    type character varying(20)
);


--
-- Name: venues_id_seq; Type: SEQUENCE; Schema: agaros; Owner: -
--

CREATE SEQUENCE agaros.venues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: venues_id_seq; Type: SEQUENCE OWNED BY; Schema: agaros; Owner: -
--

ALTER SEQUENCE agaros.venues_id_seq OWNED BY agaros.venues.id;


--
-- Name: papers id; Type: DEFAULT; Schema: agaros; Owner: -
--

ALTER TABLE ONLY agaros.papers ALTER COLUMN id SET DEFAULT nextval('agaros.papers_id_seq'::regclass);


--
-- Name: urls id; Type: DEFAULT; Schema: agaros; Owner: -
--

ALTER TABLE ONLY agaros.urls ALTER COLUMN id SET DEFAULT nextval('agaros.urls_id_seq'::regclass);


--
-- Name: venues id; Type: DEFAULT; Schema: agaros; Owner: -
--

ALTER TABLE ONLY agaros.venues ALTER COLUMN id SET DEFAULT nextval('agaros.venues_id_seq'::regclass);


--
-- Name: paper_urls paper_urls_pkey; Type: CONSTRAINT; Schema: agaros; Owner: -
--

ALTER TABLE ONLY agaros.paper_urls
    ADD CONSTRAINT paper_urls_pkey PRIMARY KEY (paper_id, url_id);


--
-- Name: papers papers_pkey; Type: CONSTRAINT; Schema: agaros; Owner: -
--

ALTER TABLE ONLY agaros.papers
    ADD CONSTRAINT papers_pkey PRIMARY KEY (id);


--
-- Name: urls urls_pkey; Type: CONSTRAINT; Schema: agaros; Owner: -
--

ALTER TABLE ONLY agaros.urls
    ADD CONSTRAINT urls_pkey PRIMARY KEY (id);


--
-- Name: venues venues_pkey; Type: CONSTRAINT; Schema: agaros; Owner: -
--

ALTER TABLE ONLY agaros.venues
    ADD CONSTRAINT venues_pkey PRIMARY KEY (id);


--
-- Name: paper_urls paper_urls_paper_id_fkey; Type: FK CONSTRAINT; Schema: agaros; Owner: -
--

ALTER TABLE ONLY agaros.paper_urls
    ADD CONSTRAINT paper_urls_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES agaros.papers(id);


--
-- Name: paper_urls paper_urls_url_id_fkey; Type: FK CONSTRAINT; Schema: agaros; Owner: -
--

ALTER TABLE ONLY agaros.paper_urls
    ADD CONSTRAINT paper_urls_url_id_fkey FOREIGN KEY (url_id) REFERENCES agaros.urls(id);


--
-- Name: papers papers_venue_id_fkey; Type: FK CONSTRAINT; Schema: agaros; Owner: -
--

ALTER TABLE ONLY agaros.papers
    ADD CONSTRAINT papers_venue_id_fkey FOREIGN KEY (venue_id) REFERENCES agaros.venues(id);


--
-- PostgreSQL database dump complete
--

