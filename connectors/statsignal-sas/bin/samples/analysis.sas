/***************************************************************/
/* Program : analysis.sas                                      */
/* Purpose : Build the Northgate analysis cohort from the      */
/*           cleaned ETL outputs and summarise visit counts.   */
/***************************************************************/

LIBNAME out "/data/northgate/out";
LIBNAME an "/data/northgate/analysis";

%PUT NOTE: analysis started, SYSERR=&SYSERR.;

DATA an.cohort;
    SET out.patients_clean;
    %clean_dates(ds=work._tmp, var=visit_date);
RUN;

PROC MEANS DATA=out.visits_clean N MEAN;
    VAR visit_count;
RUN;

PROC SORT DATA=an.cohort OUT=an.cohort_sorted;
    BY patient_id;
RUN;

%fmt_report(title=Northgate Cohort Summary);

%PUT NOTE: analysis finished, SYSERR=&SYSERR.;
