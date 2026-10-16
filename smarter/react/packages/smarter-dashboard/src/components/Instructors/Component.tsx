/**
 * Instructors dashboard widget.
 *
 * This component renders a promotional card for teaching with Smarter: the
 * Smarter Instructor Guide and the Free Course Designs, 21 ready-to-teach
 * course designs (19 micro courses and 2 master classes) that are free and
 * open source. It shows the catalog's headline numbers, two scrolling
 * ribbons of every course, each linked to its course design, the three
 * formats of a micro course, and links to the catalog and the guide.
 *
 * :returns: A JSX fragment containing the instructors call-to-action widget.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <Instructors />
 */
import "@/components/Instructors/styles.css";
import { gettext, interpolateNodes } from "@smarter/common";

const DOCS_BASE_URL = "https://docs.smarter.sh";
const CATALOG = `${DOCS_BASE_URL}/smarter-instructors/example-courses`;

interface Course {
  name: string;
  path: string;
}

const STATS = [
  { value: "21", label: gettext("course designs") },
  { value: "19", label: gettext("micro courses") },
  { value: "2", label: gettext("master classes") },
  { value: "$0", label: gettext("license fees") },
];

const COURSES: Course[] = [
  { name: gettext("Prompt Engineering"), path: "micro-courses/prompt-engineering" },
  { name: gettext("Building AI Applications"), path: "micro-courses/ai-applications" },
  { name: gettext("Agentic Development"), path: "micro-courses/agentic-development" },
  { name: "Kubernetes", path: "micro-courses/kubernetes" },
  { name: gettext("Django Master Class"), path: "master-classes/django-master-class" },
  { name: gettext("The Economics of AI"), path: "micro-courses/ai-economics" },
  { name: gettext("AI Governance"), path: "micro-courses/ai-governance" },
  { name: gettext("API Design"), path: "micro-courses/api-design" },
  { name: gettext("Backend Development"), path: "micro-courses/backend-development" },
  { name: "Docker", path: "micro-courses/docker" },
  { name: gettext("AI Application Development Master Class"), path: "master-classes/ai-application-development" },
  { name: gettext("Extension Development"), path: "micro-courses/extension-development" },
  { name: gettext("Front End Development"), path: "micro-courses/frontend-development" },
  { name: gettext("Full Stack Development"), path: "micro-courses/full-stack-development" },
  { name: gettext("Infrastructure as Code"), path: "micro-courses/infrastructure-as-code" },
  { name: gettext("Open Source Participation"), path: "micro-courses/open-source" },
  { name: gettext("Secure Software"), path: "micro-courses/secure-software" },
  { name: gettext("Self-Hosting Open Models"), path: "micro-courses/self-hosted-models" },
  { name: gettext("Software Architecture"), path: "micro-courses/software-architecture" },
  { name: gettext("Software Quality"), path: "micro-courses/software-quality" },
  { name: gettext("Documentation with Sphinx"), path: "micro-courses/sphinx-documentation" },
];

const FORMATS = [
  { value: "8 hours", label: gettext("classroom bootcamp") },
  { value: "2 weeks", label: gettext("online course") },
  { value: "4 weeks", label: gettext("online course") },
];

function CourseChips({ courses, hidden }: { courses: Course[]; hidden?: boolean }) {
  return (
    <ul className="instructors-ribbon-set" aria-hidden={hidden || undefined}>
      {courses.map((course) => (
        <li key={course.path}>
          <a
            href={`${CATALOG}/${course.path}.html`}
            target="_blank"
            className="instructors-chip"
            tabIndex={hidden ? -1 : undefined}
          >
            {course.name}
          </a>
        </li>
      ))}
    </ul>
  );
}

function Instructors() {
  return (
    <>
      <section id="instructors" aria-label={gettext("Instructors")} className="col-xl-6 mb-5 mb-xl-10">
        {/* begin::Instructors widget */}
        <div className="card border-transparent h-100 instructors-card" data-bs-theme="light">
          {/* begin::Body */}
          <div className="card-body d-flex flex-column ps-xl-15 h-100 position-relative">
            {/* begin::Illustration */}
            <img
              src="/static/assets/media/illustrations/sigma-1/2.png"
              className="position-absolute top-0 end-0 h-175px me-5 mt-5 d-none d-md-block instructors-illustration"
              alt=""
            />
            {/* end::Illustration */}
            {/* begin::Title */}
            <span className="instructors-eyebrow z-index-2">{gettext("Free for instructors")}</span>
            <div className="fs-2x fw-bold text-white mt-3 mb-2 z-index-2 instructors-headline">
              {/* Translators: a headline. %(span)s is its highlighted last words, translated separately. */}
              {interpolateNodes(gettext("Teach AI with a %(span)s"), {
                span: (
                  <span className="position-relative d-inline-block">
                    {/* Translators: the highlighted words of a headline. %(span)s is their decorative underline, and stays at the end. */}
                    {interpolateNodes(gettext("real platform%(span)s"), {
                      span: (
                        <span className="position-absolute bottom-0 start-0 border-4 border-bottom w-100 instructors-underline"></span>
                      ),
                    })}
                  </span>
                ),
              })}
            </div>
            <p className="fs-6 mb-6 z-index-2 instructors-lede">
              {gettext(
                "Ready-to-teach course designs, from prompt engineering for non-programmers to Kubernetes for platform engineers, with schedules, graded assignments, rubrics and capstone projects.",
              )}
            </p>
            {/* end::Title */}
            {/* begin::Stats */}
            <dl className="instructors-stats z-index-2">
              {STATS.map((stat) => (
                <div key={stat.label} className="instructors-stat">
                  <dt>{stat.label}</dt>
                  <dd>{stat.value}</dd>
                </div>
              ))}
            </dl>
            {/* end::Stats */}
            {/* begin::Courses */}
            <nav className="instructors-ribbons z-index-2" aria-label={gettext("Free courses")}>
              {[COURSES.slice(0, 11), COURSES.slice(11)].map((courses, row) => (
                <div key={row} className="instructors-ribbon">
                  <div className={`instructors-ribbon-track${row ? " instructors-ribbon-reverse" : ""}`}>
                    <CourseChips courses={courses} />
                    <CourseChips courses={courses} hidden />
                  </div>
                </div>
              ))}
            </nav>
            {/* end::Courses */}
            {/* begin::Formats */}
            <div className="instructors-formats z-index-2">
              <span className="instructors-formats-label">{gettext("Every micro course, three ways")}</span>
              <ul>
                {FORMATS.map((format) => (
                  <li key={format.value}>
                    <strong>{format.value}</strong> {format.label}
                  </li>
                ))}
              </ul>
            </div>
            {/* end::Courses */}
            {/* begin::Action */}
            <div className="mt-auto pt-7 z-index-2">
              <a href={`${CATALOG}/index.html`} target="_blank" className="btn btn-sm fw-semibold me-2 instructors-btn">
                {gettext("Browse the free courses")}
              </a>
              <a
                href={`${DOCS_BASE_URL}/smarter-instructor.html`}
                target="_blank"
                className="btn btn-sm btn-light fw-semibold"
              >
                {gettext("Instructor Guide")}
              </a>
            </div>
            {/* end::Action */}
          </div>
          {/* end::Body */}
        </div>
        {/* end::Instructors widget */}
      </section>
    </>
  );
}

export default Instructors;
