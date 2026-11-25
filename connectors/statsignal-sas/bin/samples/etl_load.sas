/***************************************************************/
/* Program : etl_load.sas                                      */
/* Purpose : Load raw extracts for Northgate Clinical          */
/*           Analytics and build the cleaned patient and       */
/*           visit datasets used by downstream analysis.       */
/* Owner   : Northgate Clinical Analytics (fictional)          */
/***************************************************************/

LIBNAME raw "/data/northgate/raw";
LIBNAME out "/data/northgate/out";

%PUT NOTE: etl_load started for Northgate Clinical Analytics.;

DATA out.patients_clean;
    SET raw.patients_raw;
    %clean_dates(ds=work._tmp, var=admit_date);
    LENGTH site_id $8;
    site_id = "NG01";
RUN;

%PUT NOTE: patients_clean rows processed, SYSERR=&SYSERR.;

DATA work.visit_tmp;
    SET raw.visits_raw;
RUN;

DATA out.visits_clean;
    SET work.visit_tmp;
RUN;

%PUT NOTE: etl_load finished, SYSERR=&SYSERR.;
