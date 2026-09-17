--
-- PostgreSQL database dump
--

\restrict hJmoMS8OAaWuTeafcfRm3KslsOUNygZLLkllDu0FJfhRHN4ELpLbXratYaco4t1

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: citas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.citas (
    id_lead bigint,
    fecha_solicitud timestamp without time zone NOT NULL,
    fecha_cita timestamp without time zone NOT NULL,
    cliente character varying(200) NOT NULL,
    asesor character varying(150),
    gerente character varying(150),
    asistencia character varying(30),
    n_cita character varying(30) NOT NULL,
    producto character varying(150),
    tipo_cita character varying(100),
    captacion character varying(100),
    registrado_crm boolean,
    ventas integer
);


ALTER TABLE public.citas OWNER TO postgres;

--
-- Name: interesados; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.interesados (
    nombre_apellido character varying(200),
    email character varying(254) NOT NULL,
    telefono character varying(50),
    telefono_2 character varying(50),
    id_portal integer NOT NULL,
    fecha timestamp without time zone NOT NULL,
    id_aviso bigint NOT NULL,
    codigo character varying(20),
    provincia character varying(100),
    ciudad character varying(100),
    barrio character varying(150),
    tipo_propiedad character varying(100),
    tipo_operacion character varying(50),
    precio numeric(14,2)
);


ALTER TABLE public.interesados OWNER TO postgres;

--
-- Name: leads_crm; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leads_crm (
    id_lead bigint NOT NULL,
    nombre character varying(100),
    apellido character varying(100),
    email character varying(254),
    telefono character varying(100),
    portal_origen character varying(100),
    tipo character varying(50),
    operacion character varying(50),
    precio bigint,
    estado character varying(100),
    municipio character varying(100),
    colonia character varying(150),
    fecha_registro timestamp without time zone,
    asesor_origen character varying(150),
    codigo_asesor character varying(50),
    email_asesor character varying(254),
    gerente character varying(150),
    fue_traspasado boolean,
    traspasador character varying(150),
    traspasado_a character varying(150),
    fecha_ultimo_traspaso timestamp without time zone,
    dio_seguimiento boolean,
    fecha_primer_seguimiento timestamp without time zone,
    total_actividades integer,
    llamadas integer,
    citas_registradas integer,
    citas_agendadas integer,
    citas_atendidas integer,
    citas_reagendadas integer,
    citas_canceladas integer,
    videollamadas integer,
    fue_perfilado boolean,
    fecha_perfilamiento timestamp without time zone,
    fecha_ultima_actividad timestamp without time zone,
    ultimo_asesor_activo character varying(150),
    abierto boolean,
    hubo_venta_pago boolean,
    solo_firmado boolean,
    monto_venta numeric(14,2),
    fecha_cierre timestamp without time zone,
    fecha_cierre_venta timestamp without time zone,
    dias_activo integer,
    id_aviso bigint
);


ALTER TABLE public.leads_crm OWNER TO postgres;

--
-- Name: portales; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.portales (
    id_portal integer NOT NULL,
    nombre character varying(50) NOT NULL,
    area character varying(30) NOT NULL
);


ALTER TABLE public.portales OWNER TO postgres;

--
-- Name: semanas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.semanas (
    id_semana integer NOT NULL,
    inicio_semana timestamp without time zone NOT NULL,
    fin_semana timestamp without time zone NOT NULL
);


ALTER TABLE public.semanas OWNER TO postgres;

--
-- Name: stats_portales; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stats_portales (
    periodo date NOT NULL,
    exposicion integer,
    visualizaciones integer,
    consultas_recibidas integer,
    completaron_formulario integer,
    contactaron_por_whatsapp integer,
    vieron_tus_datos integer,
    id_portal integer NOT NULL
);


ALTER TABLE public.stats_portales OWNER TO postgres;

--
-- Name: citas citas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.citas
    ADD CONSTRAINT citas_pkey PRIMARY KEY (cliente, fecha_solicitud, fecha_cita, n_cita);


--
-- Name: interesados interesados_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.interesados
    ADD CONSTRAINT interesados_pkey PRIMARY KEY (email, fecha, id_portal, id_aviso);


--
-- Name: leads_crm leads_crm_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leads_crm
    ADD CONSTRAINT leads_crm_pkey PRIMARY KEY (id_lead);


--
-- Name: portales portales_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.portales
    ADD CONSTRAINT portales_pkey PRIMARY KEY (id_portal);


--
-- Name: semanas semanas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semanas
    ADD CONSTRAINT semanas_pkey PRIMARY KEY (id_semana);


--
-- Name: stats_portales stats_portales_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_portales
    ADD CONSTRAINT stats_portales_pkey PRIMARY KEY (periodo, id_portal);


--
-- Name: citas citas_id_lead_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.citas
    ADD CONSTRAINT citas_id_lead_fkey FOREIGN KEY (id_lead) REFERENCES public.leads_crm(id_lead);


--
-- Name: interesados interesados_id_portal_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.interesados
    ADD CONSTRAINT interesados_id_portal_fkey FOREIGN KEY (id_portal) REFERENCES public.portales(id_portal);


--
-- Name: stats_portales stats_portales_id_portal_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_portales
    ADD CONSTRAINT stats_portales_id_portal_fkey FOREIGN KEY (id_portal) REFERENCES public.portales(id_portal);


--
-- PostgreSQL database dump complete
--

\unrestrict hJmoMS8OAaWuTeafcfRm3KslsOUNygZLLkllDu0FJfhRHN4ELpLbXratYaco4t1

