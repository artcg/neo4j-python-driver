# Copyright (c) "Neo4j"
# Neo4j Sweden AB [http://neo4j.com]
#
# This file is part of Neo4j.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
This module contains the core driver exceptions.

Driver API Errors
=================
+ Neo4jError
  + ClientError
    + CypherSyntaxError
    + CypherTypeError
    + ConstraintError
    + AuthError
      + TokenExpired
    + Forbidden
  + DatabaseError
  + TransientError
    + DatabaseUnavailable
    + NotALeader
    + ForbiddenOnReadOnlyDatabase

+ DriverError
  + TransactionError
    + TransactionNestingError
  + ResultError
    + ResultConsumedError
    + ResultNotSingleError
  + SessionExpired
  + ServiceUnavailable
    + RoutingServiceUnavailable
    + WriteServiceUnavailable
    + ReadServiceUnavailable
    + IncompleteCommit
  + ConfigurationError
    + AuthConfigurationError
    + CertificateConfigurationError

Connector API Errors
====================
+ BoltError
  + BoltHandshakeError
  + BoltRoutingError
  + BoltConnectionError
      + BoltSecurityError
      + BoltConnectionBroken
      + BoltConnectionClosed
  + BoltFailure
  + BoltProtocolError
  + Bolt*

"""

CLASSIFICATION_CLIENT = "ClientError"
CLASSIFICATION_TRANSIENT = "TransientError"
CLASSIFICATION_DATABASE = "DatabaseError"


class Neo4jError(Exception):
    """ Raised when the Cypher engine returns an error to the client.
    """

    message = None
    code = None
    classification = None
    category = None
    title = None
    metadata = None

    @classmethod
    def hydrate(cls, message=None, code=None, **metadata):
        message = message or "An unknown error occurred"
        code = code or "Neo.DatabaseError.General.UnknownError"
        try:
            _, classification, category, title = code.split(".")
            if code == "Neo.ClientError.Security.AuthorizationExpired":
                classification = CLASSIFICATION_TRANSIENT
        except ValueError:
            classification = CLASSIFICATION_DATABASE
            category = "General"
            title = "UnknownError"

        error_class = cls._extract_error_class(classification, code)

        inst = error_class(message)
        inst.message = message
        inst.code = code
        inst.classification = classification
        inst.category = category
        inst.title = title
        inst.metadata = metadata
        return inst

    @classmethod
    def _extract_error_class(cls, classification, code):
        if classification == CLASSIFICATION_CLIENT:
            try:
                return client_errors[code]
            except KeyError:
                return ClientError

        elif classification == CLASSIFICATION_TRANSIENT:
            try:
                return transient_errors[code]
            except KeyError:
                return TransientError

        elif classification == CLASSIFICATION_DATABASE:
            return DatabaseError

        else:
            return cls

    def invalidates_all_connections(self):
        return self.code == "Neo.ClientError.Security.AuthorizationExpired"

    def is_fatal_during_discovery(self):
        # checks if the code is an error that is caused by the client. In this
        # case the driver should fail fast during discovery.
        if not isinstance(self.code, str):
            return False
        if self.code in ("Neo.ClientError.Database.DatabaseNotFound",
                         "Neo.ClientError.Transaction.InvalidBookmark",
                         "Neo.ClientError.Transaction.InvalidBookmarkMixture"):
            return True
        if (self.code.startswith("Neo.ClientError.Security.")
                and self.code != "Neo.ClientError.Security."
                                 "AuthorizationExpired"):
            return True
        return False

    def __str__(self):
        return "{{code: {code}}} {{message: {message}}}".format(code=self.code, message=self.message)


class ClientError(Neo4jError):
    """ The Client sent a bad request - changing the request might yield a successful outcome.
    """


class DatabaseError(Neo4jError):
    """ The database failed to service the request.
    """


class TransientError(Neo4jError):
    """ The database cannot service the request right now, retrying later might yield a successful outcome.
    """

    def is_retriable(self):
        """These are really client errors but classification on the server is not entirely correct and they are classified as transient.

        :return: True if it is a retriable TransientError, otherwise False.
        :rtype: bool
        """
        return not (self.code in (
            "Neo.TransientError.Transaction.Terminated",
            "Neo.TransientError.Transaction.LockClientStopped",
        ))


class DatabaseUnavailable(TransientError):
    """
    """


class ConstraintError(ClientError):
    """
    """


class CypherSyntaxError(ClientError):
    """
    """


class CypherTypeError(ClientError):
    """
    """


class NotALeader(TransientError):
    """
    """


class Forbidden(ClientError):
    """
    """


class ForbiddenOnReadOnlyDatabase(TransientError):
    """
    """


class AuthError(ClientError):
    """ Raised when authentication failure occurs.
    """


class TokenExpired(AuthError):
    """ Raised when the authentication token has expired.

    A new driver instance with a fresh authentication token needs to be created.
    """

client_errors = {

    # ConstraintError
    "Neo.ClientError.Schema.ConstraintValidationFailed": ConstraintError,
    "Neo.ClientError.Schema.ConstraintViolation": ConstraintError,
    "Neo.ClientError.Statement.ConstraintVerificationFailed": ConstraintError,
    "Neo.ClientError.Statement.ConstraintViolation": ConstraintError,

    # CypherSyntaxError
    "Neo.ClientError.Statement.InvalidSyntax": CypherSyntaxError,
    "Neo.ClientError.Statement.SyntaxError": CypherSyntaxError,

    # CypherTypeError
    "Neo.ClientError.Procedure.TypeError": CypherTypeError,
    "Neo.ClientError.Statement.InvalidType": CypherTypeError,
    "Neo.ClientError.Statement.TypeError": CypherTypeError,

    # Forbidden
    "Neo.ClientError.General.ForbiddenOnReadOnlyDatabase": ForbiddenOnReadOnlyDatabase,
    "Neo.ClientError.General.ReadOnly": Forbidden,
    "Neo.ClientError.Schema.ForbiddenOnConstraintIndex": Forbidden,
    "Neo.ClientError.Schema.IndexBelongsToConstraint": Forbidden,
    "Neo.ClientError.Security.Forbidden": Forbidden,
    "Neo.ClientError.Transaction.ForbiddenDueToTransactionType": Forbidden,

    # AuthError
    "Neo.ClientError.Security.AuthorizationFailed": AuthError,
    "Neo.ClientError.Security.Unauthorized": AuthError,

    # TokenExpired
    "Neo.ClientError.Security.TokenExpired": TokenExpired,

    # NotALeader
    "Neo.ClientError.Cluster.NotALeader": NotALeader,
}

transient_errors = {

    # DatabaseUnavailableError
    "Neo.TransientError.General.DatabaseUnavailable": DatabaseUnavailable
}


class DriverError(Exception):
    """ Raised when the Driver raises an error.
    """


class SessionExpired(DriverError):
    """ Raised when a session is no longer able to fulfil
    the purpose described by its original parameters.
    """

    def __init__(self, session, *args, **kwargs):
        super(SessionExpired, self).__init__(session, *args, **kwargs)


class TransactionError(DriverError):
    """ Raised when an error occurs while using a transaction.
    """

    def __init__(self, transaction, *args, **kwargs):
        super(TransactionError, self).__init__(*args, **kwargs)
        self.transaction = transaction


class TransactionNestingError(DriverError):
    """ Raised when transactions are nested incorrectly.
    """

    def __init__(self, transaction, *args, **kwargs):
        super(TransactionError, self).__init__(*args, **kwargs)
        self.transaction = transaction


class ResultError(DriverError):
    """Raised when an error occurs while using a result object."""

    def __init__(self, result, *args, **kwargs):
        super(ResultError, self).__init__(*args, **kwargs)
        self.result = result


class ResultConsumedError(ResultError):
    """Raised when trying to access records of a consumed result."""


class ResultNotSingleError(ResultError):
    """Raised when result.single() detects not exactly one record in result."""


class ServiceUnavailable(DriverError):
    """ Raised when no database service is available.
    """


class RoutingServiceUnavailable(ServiceUnavailable):
    """ Raised when no routing service is available.
    """


class WriteServiceUnavailable(ServiceUnavailable):
    """ Raised when no write service is available.
    """


class ReadServiceUnavailable(ServiceUnavailable):
    """ Raised when no read service is available.
    """


class IncompleteCommit(ServiceUnavailable):
    """ Raised when the client looses connection while committing a transaction

    Raised when a disconnection occurs while still waiting for a commit
    response. For non-idempotent write transactions, this leaves the data
    in an unknown state with regard to whether the transaction completed
    successfully or not.
    """


class ConfigurationError(DriverError):
    """ Raised when there is an error concerning a configuration.
    """


class AuthConfigurationError(ConfigurationError):
    """ Raised when there is an error with the authentication configuration.
    """


class CertificateConfigurationError(ConfigurationError):
    """ Raised when there is an error with the authentication configuration.
    """


class UnsupportedServerProduct(Exception):
    """ Raised when an unsupported server product is detected.
    """
