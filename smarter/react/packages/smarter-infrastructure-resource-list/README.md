# @smarter/infrastructure-resource-list

The Infrastructure Resources page of the Smarter web console: the ledger of the cloud resources
that the platform has created and destroyed, whichever cloud provider created them. DNS zones
and records, TLS certificates, and billable Kubernetes resources, such as volumes and load
balancers, are recorded as the platform creates and destroys them.

The page is for superusers only, and is read-only: the platform writes the ledger.

## How it is wired

- Django view: `smarter.apps.infrastructure.views.listview.InfrastructureResourceListView`, at
  `/infrastructure/`, renders `templates/react/infrastructure-resource-list.html`.
- Template tag: `smarter.apps.infrastructure.templatetags.react_infrastructure_resource_list`.
- List api: `smarter.apps.infrastructure.views.listview.InfrastructureResourceListApiView`, at
  `/infrastructure/react-integration/api/listview/`, returns `{"summary": {...}, "objects": [...]}`.
- Model: `smarter.apps.infrastructure.models.InfrastructureResource`.

## Development

```console
npm run dev -w @smarter/infrastructure-resource-list
npm run storybook -w @smarter/infrastructure-resource-list
npm run test -w @smarter/infrastructure-resource-list
npm run build -w @smarter/infrastructure-resource-list
```

The build is written to `smarter/smarter/static/react/@smarter/infrastructure-resource-list/`.
