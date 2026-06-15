import React from 'react';
import Layout from '@theme/Layout';
import ThemedImage from '@theme/ThemedImage';
import CodeBlock from '@theme/CodeBlock';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './index.module.css';

function Badge({href, src, alt}) {
  const img = <img src={src} alt={alt} height={20} />;
  return href ? <a href={href}>{img}</a> : img;
}

export default function Home() {
  return (
    <Layout description="Conversations Are Prototypes. Skills Are Artifacts.">
      <main className={styles.main}>
        <div className={styles.hero}>
          <ThemedImage
            alt="skillify"
            sources={{
              light: useBaseUrl('/img/skillify-banner-light.svg'),
              dark: useBaseUrl('/img/skillify-banner-dark.svg'),
            }}
            width={500}
          />
          <h3 className={styles.tagline}>
            <em>Conversations Are Prototypes. Skills Are Artifacts.</em>
          </h3>
          <div className={styles.badges}>
            <Badge
              href="https://github.com/nickommen/skillify/actions/workflows/ci.yml"
              src="https://img.shields.io/github/actions/workflow/status/nickommen/skillify/ci.yml?branch=main&style=flat-square"
              alt="CI"
            />
            <Badge
              src="https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white"
              alt="Python 3.12+"
            />
            <Badge
              href="https://github.com/nickommen/skillify/blob/main/LICENSE"
              src="https://img.shields.io/badge/license-MIT-green?style=flat-square"
              alt="MIT License"
            />
          </div>
        </div>

        <div className={styles.content}>
          <p>
            Skillify converts a Claude Code conversation — where you iterated on
            automating a task — into a deterministic Python-scripted skill. It
            parses the conversation, extracts the workflow, and generates Python
            scripts + a SKILL.md wrapper. Future runs are deterministic, using AI
            only for error recovery and semantic summarization.
          </p>

          <h2>Prerequisites</h2>
          <ul>
            <li>Python 3.12+</li>
            <li>Claude Code with skill support</li>
          </ul>

          <h2>Installation</h2>
          <CodeBlock language="bash">
            {`git clone https://github.com/nickommen/skillify.git
cd skillify
./install.sh`}
          </CodeBlock>
          <p>Or manually:</p>
          <CodeBlock language="bash">
            {`git clone https://github.com/nickommen/skillify.git
ln -sf "$(pwd)/skillify" ~/.claude/skills/skillify`}
          </CodeBlock>
          <p>
            After installation, <code>/skillify</code> will be available in
            Claude Code.
          </p>

          <h2>Usage</h2>
          <CodeBlock language="bash">
            {`# Skillify the current conversation
/skillify
/skillify this

# Skillify a specific past conversation by session ID
/skillify 15555f6f-ed1d-47fb-b542-efdaff259864`}
          </CodeBlock>
          <p>
            Also triggers on natural language: &quot;turn this into a
            skill&quot;, &quot;make this a skill&quot;, &quot;create a skill from
            this conversation&quot;, &quot;convert this to a skill&quot;
          </p>

          <h2>How It Works</h2>
          <ol>
            <li>
              <strong>Identify</strong> the source conversation — current session
              or explicit session UUID
            </li>
            <li>
              <strong>Parse</strong> the conversation JSONL into a compact
              workflow manifest
            </li>
            <li>
              <strong>Interview</strong> the user to confirm skill name,
              description, save location, and workflow steps
            </li>
            <li>
              <strong>Check</strong> if the conversation already produced Python
              scripts — reuse if possible
            </li>
            <li>
              <strong>Generate</strong> Python scripts, validators, and SKILL.md
              via an Agent reading the manifest
            </li>
            <li>
              <strong>Preview</strong> generated files for user confirmation
              before writing
            </li>
            <li>
              <strong>Write and validate</strong> generated Python syntax and
              YAML frontmatter
            </li>
            <li>
              <strong>Report</strong> created files, tool dependencies, env vars
              needed, and how to invoke
            </li>
          </ol>

          <h2>Generated Skill Structure</h2>
          <CodeBlock language="text">
            {`skill-name/
  SKILL.md              # Orchestration procedure (under 500 lines)
  README.md             # Documentation and setup instructions
  scripts/
    run.py              # Main deterministic script (stdlib-only)
    validators.py       # Precondition checks and output validation
  skill.schema.json     # Input/output schema (when applicable)`}
          </CodeBlock>
          <p>
            Generated skills are <strong>deterministic</strong>,{' '}
            <strong>composable</strong> (invokable via{' '}
            <code>/skill-name</code>), and <strong>self-validating</strong>.
          </p>

          <h2>Contributing</h2>
          <p>
            See the{' '}
            <a href="https://github.com/nickommen/skillify/blob/main/CONTRIBUTING.md">
              Contributing Guide
            </a>{' '}
            for development setup and guidelines.
          </p>

          <h2>License</h2>
          <p>
            <a href="https://github.com/nickommen/skillify/blob/main/LICENSE">
              MIT
            </a>
          </p>
        </div>
      </main>
    </Layout>
  );
}
