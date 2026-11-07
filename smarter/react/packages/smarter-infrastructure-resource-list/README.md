# @smarter/infrastructure-resource-list

The Infrastructure Resources page of the Smarter web console: the ledger of the cloud resources
that the platform has created and destroyed, whichever cloud provider created them. DNS zones
and records, TLS certificates, and billable Kubernetes resources, such as volumes and load
balancers, are recorded as the platform creates and destroys them.

The page is for superusers only, and is read-only: the platform writes the ledger.

## How it is wired

- Console: `@smarter/console` renders this package's `InfrastructureResourceList` at
  `/infrastructure/` for a superuser, and shows anyone else that the page is not found
  (`smarter-console/src/lib/lists.ts`).
- Django page: `smarter.apps.infrastructure.views.listview.InfrastructureResourceListView`, a
  `ConsoleAppView` subclass that keeps the page's url name.
- List api: `smarter.apps.infrastructure.views.listview.InfrastructureResourceListApiView`, at
  `/api/web/infrastructure/listview/`, returns `{"summary": {...}, "objects": [...]}`.
- Model: `smarter.apps.infrastructure.models.InfrastructureResource`.

## Development

```console
npm run dev -w @smarter/infrastructure-resource-list
npm run storybook -w @smarter/infrastructure-resource-list
npm run test -w @smarter/infrastructure-resource-list
```

The package has no build of its own: the console's build bundles it.
