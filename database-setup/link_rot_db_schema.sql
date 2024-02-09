--
-- PostgreSQL database dump
--

-- Dumped from database version 13.11 (Debian 13.11-0+deb11u1)
-- Dumped by pg_dump version 13.11 (Debian 13.11-0+deb11u1)

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
-- Name: user_schema; Type: SCHEMA; Schema: -; Owner: user_schema
--

CREATE SCHEMA user_schema;


ALTER SCHEMA user_schema OWNER TO user_schema;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: paper_urls; Type: TABLE; Schema: user_schema; Owner: user_schema
--

CREATE TABLE user_schema.paper_urls (
    paper_id integer NOT NULL,
    url_id integer NOT NULL
);


ALTER TABLE user_schema.paper_urls OWNER TO user_schema;

--
-- Name: papers; Type: TABLE; Schema: user_schema; Owner: user_schema
--

CREATE TABLE user_schema.papers (
    id integer NOT NULL,
    venue_id integer,
    year integer,
    ee character varying(500),
    doi text
);


ALTER TABLE user_schema.papers OWNER TO user_schema;

--
-- Name: papers_id_seq; Type: SEQUENCE; Schema: user_schema; Owner: user_schema
--

CREATE SEQUENCE user_schema.papers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE user_schema.papers_id_seq OWNER TO user_schema;

--
-- Name: papers_id_seq; Type: SEQUENCE OWNED BY; Schema: user_schema; Owner: user_schema
--

ALTER SEQUENCE user_schema.papers_id_seq OWNED BY user_schema.papers.id;


--
-- Name: urls; Type: TABLE; Schema: user_schema; Owner: user_schema
--

CREATE TABLE user_schema.urls (
    id integer NOT NULL,
    url character varying(500) NOT NULL,
    active boolean,
    status_code integer DEFAULT 0,
    network_error integer,
    section character varying(500)
);


ALTER TABLE user_schema.urls OWNER TO user_schema;

--
-- Name: urls_id_seq; Type: SEQUENCE; Schema: user_schema; Owner: user_schema
--

CREATE SEQUENCE user_schema.urls_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE user_schema.urls_id_seq OWNER TO user_schema;

--
-- Name: urls_id_seq; Type: SEQUENCE OWNED BY; Schema: user_schema; Owner: user_schema
--

ALTER SEQUENCE user_schema.urls_id_seq OWNED BY user_schema.urls.id;


--
-- Name: venues; Type: TABLE; Schema: user_schema; Owner: user_schema
--

CREATE TABLE user_schema.venues (
    id integer NOT NULL,
    acronym character varying(20) NOT NULL,
    name character varying(200),
    type character varying(20)
);


ALTER TABLE user_schema.venues OWNER TO user_schema;

--
-- Name: venues_id_seq; Type: SEQUENCE; Schema: user_schema; Owner: user_schema
--

CREATE SEQUENCE user_schema.venues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE user_schema.venues_id_seq OWNER TO user_schema;

--
-- Name: venues_id_seq; Type: SEQUENCE OWNED BY; Schema: user_schema; Owner: user_schema
--

ALTER SEQUENCE user_schema.venues_id_seq OWNED BY user_schema.venues.id;


--
-- Name: papers id; Type: DEFAULT; Schema: user_schema; Owner: user_schema
--

ALTER TABLE ONLY user_schema.papers ALTER COLUMN id SET DEFAULT nextval('user_schema.papers_id_seq'::regclass);


--
-- Name: urls id; Type: DEFAULT; Schema: user_schema; Owner: user_schema
--

ALTER TABLE ONLY user_schema.urls ALTER COLUMN id SET DEFAULT nextval('user_schema.urls_id_seq'::regclass);


--
-- Name: venues id; Type: DEFAULT; Schema: user_schema; Owner: user_schema
--

ALTER TABLE ONLY user_schema.venues ALTER COLUMN id SET DEFAULT nextval('user_schema.venues_id_seq'::regclass);


--
-- Name: paper_urls paper_urls_pkey; Type: CONSTRAINT; Schema: user_schema; Owner: user_schema
--

ALTER TABLE ONLY user_schema.paper_urls
    ADD CONSTRAINT paper_urls_pkey PRIMARY KEY (paper_id, url_id);


--
-- Name: papers papers_pkey; Type: CONSTRAINT; Schema: user_schema; Owner: user_schema
--

ALTER TABLE ONLY user_schema.papers
    ADD CONSTRAINT papers_pkey PRIMARY KEY (id);


--
-- Name: urls urls_pkey; Type: CONSTRAINT; Schema: user_schema; Owner: user_schema
--

ALTER TABLE ONLY user_schema.urls
    ADD CONSTRAINT urls_pkey PRIMARY KEY (id);


--
-- Name: venues venues_pkey; Type: CONSTRAINT; Schema: user_schema; Owner: user_schema
--

ALTER TABLE ONLY user_schema.venues
    ADD CONSTRAINT venues_pkey PRIMARY KEY (id);


--
-- Name: paper_urls paper_urls_paper_id_fkey; Type: FK CONSTRAINT; Schema: user_schema; Owner: user_schema
--

ALTER TABLE ONLY user_schema.paper_urls
    ADD CONSTRAINT paper_urls_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES user_schema.papers(id);


--
-- Name: paper_urls paper_urls_url_id_fkey; Type: FK CONSTRAINT; Schema: user_schema; Owner: user_schema
--

ALTER TABLE ONLY user_schema.paper_urls
    ADD CONSTRAINT paper_urls_url_id_fkey FOREIGN KEY (url_id) REFERENCES user_schema.urls(id);


--
-- Name: papers papers_venue_id_fkey; Type: FK CONSTRAINT; Schema: user_schema; Owner: user_schema
--

ALTER TABLE ONLY user_schema.papers
    ADD CONSTRAINT papers_venue_id_fkey FOREIGN KEY (venue_id) REFERENCES user_schema.venues(id);


--
-- PostgreSQL database dump complete
--

